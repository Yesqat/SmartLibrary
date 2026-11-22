"use client";

import {
  useEffectEvent,
  useLayoutEffect,
  useRef,
  type CSSProperties,
} from "react";
import { createPortal } from "react-dom";
import { BookOpen } from "lucide-react";
import type { BookCoverSnapshot } from "./book-transition-geometry";
import cardStyles from "./book-card.module.css";
import styles from "./book-transition.module.css";

type Props = {
  cover: BookCoverSnapshot;
  revealing: boolean;
  onNavigate: () => void;
  onOpened: () => void;
  onFinished: () => void;
  onCancel: () => void;
};

export function BookTransitionOverlay({
  cover,
  revealing,
  onNavigate,
  onOpened,
  onFinished,
  onCancel,
}: Props) {
  const root = useRef<HTMLDivElement>(null);
  const backdrop = useRef<HTMLDivElement>(null);
  const flight = useRef<HTMLDivElement>(null);
  const shadow = useRef<HTMLDivElement>(null);
  const model = useRef<HTMLDivElement>(null);
  const lid = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const navigate = useEffectEvent(onNavigate);
  const opened = useEffectEvent(onOpened);
  const finished = useEffectEvent(onFinished);
  const cancel = useEffectEvent(onCancel);

  useLayoutEffect(() => {
    const stage = root.current!;
    let active = true;
    const animations: Animation[] = [];
    const play = (node: Element, frames: Keyframe[], duration: number) => {
      const animation = node.animate(frames, { duration, fill: "both" });
      animations.push(animation);
      return animation;
    };
    try {
      const { left, top, width, height } = cover.rect;
      const vw = stage.clientWidth;
      const vh = stage.clientHeight;
      const duration = vw < 640 ? 910 : 1070;
      // Reserve room for both boards, including their perspective foreshortening.
      const scale = Math.min(
        (vw * 0.418) / width,
        (vh * 0.63) / height,
        480 / height,
      );
      const endX = vw * 0.49;
      const endY = (vh - height * scale) / 2;
      // A wide cover may already occupy more than half a phone. Lift it
      // while closed, then make room for the second board as it opens.
      const liftScale = Math.min(
        1.24,
        (vw * 0.86) / width,
        (vh * 0.78) / height,
      );
      const move = (x: number, y: number, s: number) =>
        `translate3d(${x}px, ${y}px, 0) scale(${s})`;

      if (cover.kind === "image") {
        // Paint from the decoded catalogue image before hiding it. A second
        // img could need another fetch/decode even for the same currentSrc.
        const surface = canvas.current!;
        const { naturalWidth, naturalHeight } = cover.image;
        const resolution = Math.min(
          1,
          1600 / Math.max(naturalWidth, naturalHeight),
        );
        surface.width = Math.max(1, Math.round(naturalWidth * resolution));
        surface.height = Math.max(1, Math.round(naturalHeight * resolution));
        const context = surface.getContext("2d");
        if (!context) throw new Error("Canvas unavailable");
        context.drawImage(cover.image, 0, 0, surface.width, surface.height);
      }
      cover.source.classList.add(styles.hiddenSource);
      const easeOut = "cubic-bezier(.2,.68,.24,1)";
      const easeOpen = "cubic-bezier(.35,.04,.17,1)";
      play(
        flight.current!,
        [
          { transform: move(left, top, 1), easing: easeOut },
          ...(liftScale > scale
            ? [
                {
                  transform: move(
                    (vw - width * liftScale) / 2,
                    (vh - height * liftScale) / 2 - 3,
                    liftScale,
                  ),
                  offset: 0.31,
                  easing: easeOpen,
                },
              ]
            : []),
          {
            transform: move(endX - width * scale * 0.36, endY - 3, scale),
            offset: liftScale > scale ? 0.59 : 0.46,
            easing: easeOpen,
          },
          { transform: move(endX, endY, scale) },
        ],
        duration,
      );
      play(
        model.current!,
        [
          {
            transform: `rotateZ(${cover.rotation}deg) rotateX(0deg) rotateY(0deg)`,
            easing: easeOut,
          },
          {
            transform: "rotateZ(-3deg) rotateX(5deg) rotateY(-11deg)",
            offset: 0.43,
            easing: easeOpen,
          },
          { transform: "rotateZ(-2deg) rotateX(6deg) rotateY(7deg)" },
        ],
        duration,
      );
      play(
        shadow.current!,
        [
          { opacity: 0, transform: "scaleX(.5)", easing: easeOut },
          {
            opacity: 0.66,
            transform: "scaleX(.72)",
            offset: 0.44,
            easing: easeOpen,
          },
          { opacity: 0.82, transform: "translateX(-32%) scaleX(1.25)" },
        ],
        duration,
      );
      play(
        lid.current!,
        [
          { transform: "rotateY(0deg)" },
          { transform: "rotateY(0deg)", offset: 0.3, easing: easeOpen },
          { transform: "rotateY(-157deg)" },
        ],
        duration,
      );
      model
        .current!.querySelectorAll<HTMLElement>("[data-leaf-angle]")
        .forEach((leaf, i) => {
          const z = `translateZ(-${1.8 - i * 0.45}px)`;
          play(
            leaf,
            [
              { transform: `${z} rotateY(0deg)` },
              {
                transform: `${z} rotateY(0deg)`,
                offset: 0.52 - i * 0.04,
                easing: easeOpen,
              },
              { transform: `${z} rotateY(${leaf.dataset.leafAngle}deg)` },
            ],
            duration,
          );
        });
      const background = play(
        backdrop.current!,
        [{ opacity: 0, easing: "ease-in-out" }, { opacity: 1 }],
        duration * 0.37,
      );
      // Commit the route behind the opaque backdrop, as the hinge starts moving.
      void background.finished.then(
        () => {
          if (active) navigate();
        },
        () => {},
      );
      void Promise.all(animations.map((animation) => animation.finished)).then(
        () => {
          if (active) {
            stage.dataset.phase = "open";
            opened();
          }
        },
        () => {
          if (active) cancel();
        },
      );
    } catch {
      cancel();
    }
    return () => {
      active = false;
      animations.forEach((animation) => animation.cancel());
      cover.source.classList.remove(styles.hiddenSource);
    };
  }, [cover]);

  useLayoutEffect(() => {
    if (!revealing) return;
    let active = true;
    let fade: Animation | undefined;
    try {
      fade = root.current!.animate([{ opacity: 1 }, { opacity: 0 }], {
        duration: 180,
        easing: "ease-out",
        fill: "forwards",
      });
      void fade.finished.then(
        () => {
          if (active) finished();
        },
        () => {
          if (active) cancel();
        },
      );
    } catch {
      cancel();
    }
    return () => {
      active = false;
      fade?.cancel();
    };
  }, [revealing]);

  if (typeof document === "undefined") return null;
  const dimensions = {
    width: cover.rect.width,
    height: cover.rect.height,
    "--depth": `${Math.min(7, Math.max(3, cover.rect.width * 0.034))}px`,
    "--perspective": `${Math.max(520, cover.rect.width * 5.5)}px`,
    ...(cover.kind === "jacket" && {
      "--cloth": cover.cloth,
      "--foil": cover.foil,
    }),
  } as CSSProperties;
  return createPortal(
    <div
      ref={root}
      aria-hidden="true"
      className={styles.overlay}
      data-book-transition=""
      data-phase={revealing ? "revealing" : "opening"}
    >
      <div ref={backdrop} className={styles.backdrop} />
      <div ref={flight} className={styles.flight} style={dimensions}>
        <div ref={shadow} className={styles.shadow} />
        <div className={styles.perspective}>
          <div ref={model} className={styles.model}>
            <div className={styles.backBoard} />
            <div className={styles.foreEdge} />
            <div className={styles.footEdge} />
            <div className={styles.paperBlock} />
            {[-4, -12, -29].map((angle) => (
              <div
                key={angle}
                data-leaf-angle={angle}
                className={styles.leaf}
              />
            ))}
            <div ref={lid} className={styles.lid}>
              <div className={styles.outside}>
                {cover.kind === "image" ? (
                  <canvas ref={canvas} />
                ) : (
                  <div
                    className={`${cardStyles.jacket} ${styles.replicaJacket}`}
                  >
                    <BookOpen />
                  </div>
                )}
              </div>
              <div className={styles.inside} />
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
