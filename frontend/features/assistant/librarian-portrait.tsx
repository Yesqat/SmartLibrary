"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import type { PortraitScene } from "./librarian-scene";
import styles from "./librarian-portrait.module.css";

export function LibrarianPortrait({ isTyping }: { isTyping: boolean }) {
  const mount = useRef<HTMLDivElement>(null);
  const scene = useRef<PortraitScene | null>(null);
  const greeted = useRef(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    scene.current?.setTyping(isTyping);
  }, [isTyping, ready]);

  useEffect(() => {
    const element = mount.current;
    if (!element || !window.matchMedia || !window.WebGL2RenderingContext)
      return;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const connection = (
      navigator as Navigator & { connection?: { saveData?: boolean } }
    ).connection;
    let controller: AbortController | undefined;

    function load() {
      controller?.abort();
      scene.current = null;
      setReady(false);
      if (motion.matches || connection?.saveData || !element) {
        greeted.current = true;
        return;
      }
      const request = new AbortController();
      controller = request;
      void import("./librarian-scene")
        .then(async ({ createPortrait }) => {
          if (request.signal.aborted) return;
          const portrait = await createPortrait(element, request.signal, () => {
            scene.current = null;
            setReady(false);
            request.abort();
          });
          if (portrait && !request.signal.aborted) {
            scene.current = portrait;
            setReady(true);
            if (!greeted.current) {
              greeted.current = true;
              portrait.greet();
            }
          }
        })
        .catch(() => request.abort());
    }

    load();
    motion.addEventListener("change", load);
    return () => {
      motion.removeEventListener("change", load);
      controller?.abort();
      scene.current = null;
    };
  }, []);

  return (
    <div className={styles.portrait} data-ready={ready}>
      <Image
        src="/assistant/librarian.webp"
        alt="Көзілдірік таққан AI кітапханашы"
        fill
        loading="eager"
        sizes="(max-width: 640px) 55vw, 360px"
        className={styles.poster}
        unoptimized
      />
      <div ref={mount} className={styles.scene} aria-hidden="true" />
      {ready && (
        <input
          type="range"
          min="-12"
          max="12"
          step="1"
          defaultValue="0"
          aria-label="Кітапханашының 3D моделін бұру"
          title="3D модельді бұру"
          className={styles.rotation}
          onChange={(event) =>
            scene.current?.rotate(event.currentTarget.valueAsNumber)
          }
          onPointerMove={(event) => {
            if (event.pointerType !== "mouse" || event.buttons) return;
            const input = event.currentTarget;
            const bounds = input.getBoundingClientRect();
            input.valueAsNumber = Math.round(
              (24 * (event.clientX - bounds.left)) / bounds.width - 12,
            );
            scene.current?.rotate(input.valueAsNumber);
          }}
          onPointerLeave={(event) => {
            if (event.pointerType !== "mouse" || event.buttons) return;
            event.currentTarget.value = "0";
            scene.current?.rotate(0);
          }}
        />
      )}
    </div>
  );
}
