import { BrandMark } from "@/components/ui/brand-mark";
import { BookOpen } from "lucide-react";
import styles from "./reader-card.module.css";

export function ReaderCard() {
  return (
    <div aria-hidden="true" className={styles.art}>
      <div className={styles.card}>
        <span className={styles.wordmark}>
          <BrandMark /> SmartLibrary
        </span>
        <span className={styles.contours} />
        <span className={styles.caption}>
          <BookOpen /> Оқырман билеті
        </span>
      </div>
    </div>
  );
}
