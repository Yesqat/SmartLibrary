"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import type { LibrarianScene } from "./librarian-scene";
import styles from "./librarian-model.module.css";

const portraitAspects = {
  login: 645 / 718,
  register: 532 / 735,
  account: 436 / 425,
};

export function LibrarianModel({
  mode,
  className,
}: {
  mode: keyof typeof portraitAspects;
  className: string;
}) {
  const mount = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const aspect = portraitAspects[mode];
  const asset = `/${mode}/librarian`;

  useEffect(() => {
    const element = mount.current;
    if (
      !element ||
      !window.WebGL2RenderingContext ||
      !window.IntersectionObserver
    )
      return;

    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const connection = (
      navigator as Navigator & { connection?: { saveData?: boolean } }
    ).connection;
    let inView = false;
    let request: AbortController | undefined;
    let scene: LibrarianScene | null = null;

    function update() {
      if (motion.matches || connection?.saveData) {
        request?.abort();
        request = undefined;
        scene = null;
        setReady(false);
        return;
      }
      const visible = inView && !document.hidden;
      scene?.setVisible(visible);
      if (!visible || request || !element) return;
      const controller = new AbortController();
      request = controller;
      void import("./librarian-scene")
        .then(async ({ createLibrarianScene }) => {
          if (controller.signal.aborted) return;
          const loaded = await createLibrarianScene(
            element,
            `${asset}.glb`,
            aspect,
            controller.signal,
            () => {
              setReady(false);
              controller.abort();
            },
          );
          if (!loaded || controller.signal.aborted) return;
          scene = loaded;
          scene.setVisible(inView && !document.hidden);
          setReady(true);
        })
        .catch(() => controller.abort());
    }

    const observer = new IntersectionObserver(([entry]) => {
      inView = entry.isIntersecting;
      update();
    });
    observer.observe(element);
    motion.addEventListener("change", update);
    document.addEventListener("visibilitychange", update);
    return () => {
      observer.disconnect();
      motion.removeEventListener("change", update);
      document.removeEventListener("visibilitychange", update);
      request?.abort();
    };
  }, [asset, aspect]);

  return (
    <div
      className={className}
      style={{ aspectRatio: aspect }}
      aria-hidden="true"
    >
      <div className={styles.portrait} data-ready={ready}>
        <Image
          src={`${asset}.webp`}
          alt=""
          fill
          sizes="(max-width: 767px) 54vw, 39vw"
          loading="eager"
          unoptimized
          className={styles.poster}
        />
        <div className={styles.stage} ref={mount} />
        {mode !== "login" && (
          <svg
            className={mode === "account" ? styles.wave : styles.gesture}
            viewBox="0 0 56 68"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="m6 56 14 4m-4-31 14 12m10-35 10 22"
              stroke="currentColor"
              strokeWidth="7"
              strokeLinecap="round"
            />
          </svg>
        )}
      </div>
    </div>
  );
}
