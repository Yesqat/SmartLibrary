"use client";

import Image from "next/image";
import { type RefObject, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import styles from "./favorite-feedback.module.css";

const reducedMotion = "(prefers-reduced-motion: reduce)";

function measureFlight(
  coverUrl?: string | null,
  source?: HTMLImageElement | null,
) {
  if (
    !coverUrl ||
    !source?.isConnected ||
    !source.complete ||
    !source.naturalWidth ||
    !source.naturalHeight
  )
    return null;
  const target = document.querySelector<HTMLElement>("[data-favorites-target]");
  const nav = target?.closest("nav");
  if (!target || !nav) return null;

  const visible = { opacityProperty: true, visibilityProperty: true };
  if (
    source.checkVisibility?.(visible) === false ||
    target.checkVisibility?.(visible) === false
  )
    return null;
  const box = source.getBoundingClientRect();
  const link = target.getBoundingClientRect();
  const clip = nav.getBoundingClientRect();
  // The contained artwork and the fill image share a center (symmetric 6% padding).
  const x = box.left + box.width / 2;
  const y = box.top + box.height / 2;
  if (
    box.width <= 0 ||
    box.height <= 0 ||
    x <= 0 ||
    x >= innerWidth ||
    y <= 0 ||
    y >= innerHeight ||
    link.width <= 0 ||
    link.height <= 0 ||
    link.left < Math.max(0, clip.left) ||
    link.right > Math.min(innerWidth, clip.right) ||
    link.top < Math.max(0, clip.top) ||
    link.bottom > Math.min(innerHeight, clip.bottom)
  )
    return null;
  const src = source.currentSrc || source.src;
  if (src !== new URL(coverUrl, document.baseURI).href) return null;
  return {
    src,
    source,
    target,
    x,
    y,
    width: source.naturalWidth,
    height: source.naturalHeight,
    dx: link.left + link.width / 2 - x,
    dy: link.top + link.height / 2 - y,
  };
}

function arc(dx: number, dy: number): Keyframe[] {
  const bend = dx < 0 ? -0.15 : 0.15;
  return Array.from({ length: 13 }, (_, i) => {
    const t = i / 12;
    const lift = 4 * t * (1 - t) * bend;
    const x = dx * t + dy * lift;
    const y = dy * t - dx * lift;
    return {
      transform: `translate3d(${x}px, ${y}px, 0) scale(${1 - 0.88 * t})`,
      opacity: 1 - t ** 3,
    };
  });
}

// Both accents are local to this button, including the one painted on the nav link.
function accent(
  ref: RefObject<Animation | null>,
  element: Element,
  frames: Keyframe[],
  duration: number,
) {
  ref.current?.cancel();
  const animation = element.animate(frames, { duration, easing: "ease-out" });
  ref.current = animation;
  const release = () => {
    if (ref.current === animation) ref.current = null;
  };
  void animation.finished.then(release, release);
}

export function useFavoriteFeedback() {
  const heart = useRef<SVGSVGElement>(null);
  const copy = useRef<HTMLImageElement>(null);
  const local = useRef<Animation | null>(null);
  const [flight, setFlight] = useState<ReturnType<typeof measureFlight>>(null);

  useLayoutEffect(() => () => local.current?.cancel(), []);

  function clear() {
    local.current?.cancel();
    setFlight(null);
  }

  function play(coverUrl?: string | null, source?: HTMLImageElement | null) {
    try {
      if (
        !heart.current?.isConnected ||
        !heart.current.animate ||
        !window.matchMedia ||
        window.matchMedia(reducedMotion).matches
      )
        return;
      accent(
        local,
        heart.current,
        [
          { transform: "scale(1)" },
          { transform: "scale(1.18)", offset: 0.45 },
          { transform: "scale(1)" },
        ],
        210,
      );
      setFlight(measureFlight(coverUrl, source));
    } catch {
      // Visual feedback is optional after the server has accepted the change.
    }
  }

  useLayoutEffect(() => {
    const image = copy.current;
    if (!flight || !image) return;
    const listeners = new AbortController();
    const { signal } = listeners;
    let travel: Animation | undefined;
    const stop = () => {
      listeners.abort();
      setFlight(null);
    };
    void (async () => {
      try {
        // React may commit the portal after the page has moved.
        const motion = window.matchMedia(reducedMotion);
        const current = measureFlight(flight.src, flight.source);
        if (!current || motion.matches) return;
        image.style.left = `${current.x}px`;
        image.style.top = `${current.y}px`;
        window.addEventListener("scroll", stop, { capture: true, signal });
        window.addEventListener("resize", stop, { signal });
        motion.addEventListener("change", stop, { signal });
        travel = image.animate(arc(current.dx, current.dy), {
          duration: 650,
          easing: "ease-in-out",
          fill: "both",
        });
        await travel.finished;
        if (!signal.aborted && current.target.isConnected)
          accent(
            local,
            current.target,
            [{ backgroundColor: "#e1e7ff" }, {}],
            180,
          );
      } catch {
        // Cancelling a WAAPI animation rejects its finished promise.
      } finally {
        if (!signal.aborted) stop();
      }
    })();
    return () => {
      listeners.abort();
      travel?.cancel();
    };
  }, [flight]);

  const overlay =
    flight &&
    createPortal(
      <Image
        ref={copy}
        src={flight.src}
        width={flight.width}
        height={flight.height}
        alt=""
        aria-hidden="true"
        data-favorite-flight=""
        unoptimized
        loading="eager"
        className={styles.copy}
        style={{
          width: Math.min(56, (84 * flight.width) / flight.height),
        }}
      />,
      document.body,
    );
  return { heart, clear, play, overlay };
}
