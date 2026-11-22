type CoverRect = { left: number; top: number; width: number; height: number };

export type BookCoverSnapshot = {
  source: HTMLElement;
  rect: CoverRect;
  rotation: number;
} & (
  | { kind: "image"; image: HTMLImageElement }
  | { kind: "jacket"; cloth: string; foil: string }
);

export function measureBookCover(link: HTMLElement): BookCoverSnapshot | null {
  const image = link.querySelector<HTMLImageElement>("[data-book-cover-image]");
  if (image) {
    if (!image.complete || !image.naturalWidth || !image.naturalHeight)
      return null;
    const box = image.getBoundingClientRect();
    const style = getComputedStyle(image);
    // The fill image is border-box. Its viewport rect already includes the
    // current hover scale, but its resolved padding is in layout coordinates.
    const sx = box.width / parseFloat(style.width);
    const sy = box.height / parseFloat(style.height);
    const left = parseFloat(style.paddingLeft) * sx;
    const top = parseFloat(style.paddingTop) * sy;
    const contentWidth = box.width - left - parseFloat(style.paddingRight) * sx;
    const contentHeight =
      box.height - top - parseFloat(style.paddingBottom) * sy;
    const fit = Math.min(
      contentWidth / image.naturalWidth,
      contentHeight / image.naturalHeight,
    );
    if (!Number.isFinite(fit) || fit <= 0) return null;
    const width = image.naturalWidth * fit;
    const height = image.naturalHeight * fit;
    return {
      kind: "image",
      image,
      source: image,
      rotation: 0,
      rect: {
        left: box.left + left + (contentWidth - width) / 2,
        top: box.top + top + (contentHeight - height) / 2,
        width,
        height,
      },
    };
  }

  const jacket = link.querySelector<HTMLElement>("[data-book-cover-jacket]");
  if (!jacket) return null;
  const style = getComputedStyle(jacket);
  const box = jacket.getBoundingClientRect();
  const width = parseFloat(style.width);
  const height = parseFloat(style.height);
  // A rotated jacket's bounding box includes empty corners. Recover the
  // scaled, unrotated board around the same center for the 3D hinge.
  const matrix = style.transform
    .match(/^matrix\(([^)]+)\)$/)?.[1]
    .split(",")
    .map(Number);
  const radians = matrix ? Math.atan2(matrix[1], matrix[0]) : 0;
  const scale =
    box.width /
    (width * Math.abs(Math.cos(radians)) +
      height * Math.abs(Math.sin(radians)));
  if (!Number.isFinite(scale) || scale <= 0 || height <= 0) return null;
  return {
    kind: "jacket",
    source: jacket,
    cloth: style.getPropertyValue("--cloth"),
    foil: style.getPropertyValue("--foil"),
    rotation: (radians * 180) / Math.PI,
    rect: {
      left: box.left + (box.width - width * scale) / 2,
      top: box.top + (box.height - height * scale) / 2,
      width: width * scale,
      height: height * scale,
    },
  };
}
