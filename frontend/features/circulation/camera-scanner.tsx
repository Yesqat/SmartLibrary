"use client";
import { useEffect, useRef, useState } from "react";
import type { IScannerControls } from "@zxing/browser";
import { Button } from "@/components/ui/button";
import { librarian as t } from "@/locales/librarian";

export function CameraScanner({
  onDecoded,
  onStart,
  disabled = false,
}: {
  onDecoded: (text: string) => void;
  onStart: () => void;
  disabled?: boolean;
}) {
  const video = useRef<HTMLVideoElement>(null),
    controls = useRef<IScannerControls | null>(null),
    stream = useRef<MediaStream | null>(null),
    generation = useRef(0);
  const [active, setActive] = useState(false),
    [error, setError] = useState("");
  function release() {
    generation.current++;
    controls.current?.stop();
    controls.current = null;
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
  }
  useEffect(
    () => () => {
      generation.current++;
      controls.current?.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
    },
    [],
  );
  async function start() {
    release();
    const attempt = generation.current;
    setError("");
    setActive(true);
    onStart();
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("Unavailable");
      const acquired = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: { ideal: "environment" } },
      });
      if (attempt !== generation.current) {
        acquired.getTracks().forEach((track) => track.stop());
        return;
      }
      stream.current = acquired;
      const { BrowserQRCodeReader } = await import("@zxing/browser");
      if (attempt !== generation.current || !video.current) return;
      const scanner = await new BrowserQRCodeReader().decodeFromStream(
        acquired,
        video.current,
        (result, _error, scan) => {
          if (!result || attempt !== generation.current) return;
          scan.stop();
          release();
          setActive(false);
          onDecoded(result.getText());
        },
      );
      if (attempt !== generation.current) scanner.stop();
      else controls.current = scanner;
    } catch (cause) {
      if (attempt !== generation.current) return;
      release();
      setActive(false);
      setError(
        cause instanceof DOMException && cause.name === "NotAllowedError"
          ? t.denied
          : t.unavailable,
      );
    }
  }
  return (
    <section className="my-6 max-w-2xl rounded-xl border p-5">
      <p className="mb-4 text-sm">{t.cameraHint}</p>
      <video
        ref={video}
        muted
        playsInline
        aria-label={t.camera}
        className={`mb-4 w-full rounded-lg ${active ? "" : "hidden"}`}
      />
      {active ? (
        <Button
          variant="outline"
          onClick={() => {
            release();
            setActive(false);
          }}
        >
          {t.stopCamera}
        </Button>
      ) : (
        <Button
          disabled={disabled}
          variant="outline"
          onClick={() => void start()}
        >
          {t.camera}
        </Button>
      )}
      {error && (
        <p role="alert" className="mt-3 text-red-800">
          {error}
        </p>
      )}
    </section>
  );
}
