import { kk } from "@/locales/kk";
import Link from "next/link";
import Image from "next/image";
import { BookOpen, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RecommendationSection } from "@/features/recommendations/section";
import booksStack from "./_assets/books-stack.png";
import styles from "./home.module.css";

export default function Home() {
  return (
    <main className={styles.home}>
      <section className={styles.hero} aria-labelledby="home-heading">
        <div className={styles.heroInner}>
          <Link href="/" className={styles.logo} aria-label="SmartLibrary">
            <BookOpen aria-hidden="true" />
            <span>{kk.name}</span>
          </Link>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>{kk.name}</p>
            <h1 id="home-heading" className={styles.heading}>
              {kk.title}
            </h1>
            <p className={styles.description}>{kk.description}</p>
            <form action="/catalog" className={styles.search}>
              <label className={styles.searchField}>
                <span className="sr-only">
                  Кітап, автор, ISBN немесе тақырып
                </span>
                <Search aria-hidden="true" />
                <input
                  type="search"
                  name="q"
                  maxLength={500}
                  placeholder="Кітап, автор, ISBN немесе тақырып"
                />
              </label>
              <Button type="submit" className={styles.primaryButton}>
                Іздеу
              </Button>
            </form>
            <nav className={styles.actions} aria-label={kk.auth.account}>
              <Button
                asChild
                variant="outline"
                className={styles.secondaryButton}
              >
                <Link href="/catalog">Кітаптар каталогы</Link>
              </Button>
              <Button asChild className={styles.primaryButton}>
                <Link href="/login">{kk.auth.login}</Link>
              </Button>
              <Button
                asChild
                variant="outline"
                className={styles.secondaryButton}
              >
                <Link href="/register">{kk.auth.register}</Link>
              </Button>
            </nav>
          </div>
          <div className={styles.illustration} aria-hidden="true">
            <Image
              src={booksStack}
              alt=""
              sizes="(max-width: 639px) 300px, (max-width: 1099px) 420px, 600px"
              loading="eager"
            />
          </div>
        </div>
      </section>
      <div className={styles.popular}>
        <RecommendationSection kind="popular" />
      </div>
    </main>
  );
}
