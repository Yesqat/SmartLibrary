import Image from "next/image";
import Link from "next/link";
import { BookOpen, Compass, LogIn, Search, Sparkles } from "lucide-react";
import { BrandMark } from "@/components/ui/brand-mark";
import { Button } from "@/components/ui/button";
import { RecommendationSection } from "@/features/recommendations/section";
import { kk } from "@/locales/kk";
import orbitBook from "./_assets/orbit-book.webp";
import styles from "./home.module.css";

const searchExamples = ["Абай", "Python", "Тарих"];

export default function Home() {
  const [title, subtitle] = kk.title.split(" — ");

  return (
    <div className={styles.home} id="top">
      <header className={styles.masthead}>
        <div className={styles.headerInner}>
          <Link href="/" className={styles.brand} aria-label={kk.name}>
            <BrandMark />
            <span>{kk.name}</span>
          </Link>
          <nav className={styles.navigation} aria-label="Негізгі навигация">
            <Link href="/" aria-current="page">
              {kk.auth.home}
            </Link>
            <Link href="/catalog">Каталог</Link>
            <Link href="/catalog?mode=semantic">
              <Sparkles aria-hidden="true" />
              Мағыналық іздеу
            </Link>
          </nav>
          <nav className={styles.account} aria-label={kk.auth.account}>
            <Link className={styles.login} href="/login">
              <LogIn aria-hidden="true" />
              {kk.auth.login}
            </Link>
            <Button asChild className={styles.register}>
              <Link href="/register">{kk.auth.register}</Link>
            </Button>
          </nav>
        </div>
      </header>
      <main className={styles.main}>
        <section className={styles.hero} aria-labelledby="home-heading">
          <div className={styles.art} aria-hidden="true">
            <Image
              src={orbitBook}
              alt=""
              preload
              sizes="(max-width: 699px) 88vw, (max-width: 1439px) 52vw, 710px"
            />
          </div>
          <div className={styles.intro}>
            <p className={styles.kicker}>
              <span className={styles.signal} aria-hidden="true" />
              Цифрлық кітапхана
            </p>
            <h1 id="home-heading" className={styles.heading}>
              {title} — <em>{subtitle}</em>
            </h1>
            <p className={styles.description}>{kk.description}</p>
            <form action="/catalog" className={styles.search} role="search">
              <label className={styles.searchField}>
                <span className="sr-only">
                  Кітап, автор, ISBN немесе тақырып
                </span>
                <Search aria-hidden="true" />
                <input
                  type="search"
                  name="q"
                  maxLength={500}
                  placeholder="Кітап, автор немесе ISBN"
                />
              </label>
              <Button type="submit" className={styles.searchButton}>
                Іздеу
              </Button>
            </form>
            <div className={styles.examples}>
              <span>Мысалы</span>
              {searchExamples.map((query) => (
                <Link
                  key={query}
                  href={{ pathname: "/catalog", query: { q: query } }}
                >
                  {query}
                </Link>
              ))}
            </div>
          </div>
        </section>
        <div className={styles.shelf} id="popular">
          <p className={styles.shelfLabel}>
            <Compass aria-hidden="true" />
            Оқырман таңдауы
          </p>
          <RecommendationSection
            kind="popular"
            headingAction={
              <Link href="/catalog" className={styles.catalogLink}>
                <BookOpen aria-hidden="true" />
                Кітаптар каталогы
              </Link>
            }
          />
        </div>
      </main>
      <footer className={styles.footer}>
        <div>
          <span className={styles.footerBrand}>
            <BrandMark />
            {kk.name}
          </span>
          <a href="#top">Бет басына</a>
        </div>
      </footer>
    </div>
  );
}
