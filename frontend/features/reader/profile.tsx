"use client";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpen,
  Camera,
  ImageIcon,
  Mail,
  Phone,
  Quote,
  Save,
  ShieldCheck,
  Sprout,
  Star,
  Trash2,
  Upload,
  UserRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  CatalogShell,
  Failure,
  Field,
  inputClass,
} from "@/features/catalog/shared";
import { ReferencePicker } from "@/features/catalog/reference-picker";
import type { Reference } from "@/features/catalog/api";
import { checkSession, type User } from "@/services/api-client";
import { reader as t } from "@/locales/reader";
import { readerApi, type Preferences } from "./api";
import profileBooks from "./assets/profile-books.png";
import styles from "./profile.module.css";

function ProfileHero() {
  return (
    <div className={styles.hero}>
      <div className={styles.heroInner}>
        <div className={styles.intro}>
          <p className={styles.eyebrow}>ЖЕКЕ КАБИНЕТ</p>
          <p className={styles.title} aria-hidden="true">
            Профиль
          </p>
          <p className={styles.description}>
            Жеке мәліметтеріңізді басқарыңыз және кітапханадағы тәжірибеңізді
            ыңғайлы етіңіз.
          </p>
          <blockquote className={styles.quote}>
            <Quote aria-hidden="true" />
            <div>
              Білім өзіңнен басталады.<cite>— Абай Құнанбайұлы</cite>
            </div>
          </blockquote>
        </div>
        <div className={styles.artwork} aria-hidden="true">
          <Image
            src={profileBooks}
            alt=""
            width={1536}
            height={1024}
            sizes="(max-width: 767px) 1px, (max-width: 1199px) 45vw, 460px"
            loading="eager"
          />
          <div className={styles.motto}>
            <Sprout />
            <p>Жақсы оқырман — жақсы болашақ!</p>
            <span />
          </div>
        </div>
      </div>
    </div>
  );
}

function ProfileForm({ user }: { user: User }) {
  const cache = useQueryClient();
  const mutation = useMutation({
    mutationFn: readerApi.saveProfile,
    onSuccess: async (data) => {
      cache.setQueryData(["profile"], data);
      await checkSession();
    },
  });
  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault();
        const form = new FormData(e.currentTarget);
        mutation.mutate({
          first_name: String(form.get("first_name")),
          last_name: String(form.get("last_name")),
          phone: String(form.get("phone")) || null,
        });
      }}
    >
      <fieldset className={styles.fields} disabled={mutation.isPending}>
        <Field label={t.firstName}>
          <span className={styles.inputWrap}>
            <UserRound aria-hidden="true" />
            <input
              className={inputClass}
              name="first_name"
              defaultValue={user.first_name}
              required
              maxLength={100}
              autoComplete="given-name"
            />
          </span>
        </Field>
        <Field label={t.lastName}>
          <span className={styles.inputWrap}>
            <UserRound aria-hidden="true" />
            <input
              className={inputClass}
              name="last_name"
              defaultValue={user.last_name}
              required
              maxLength={100}
              autoComplete="family-name"
            />
          </span>
        </Field>
        <Field label={t.phone}>
          <span className={styles.inputWrap}>
            <Phone aria-hidden="true" />
            <input
              className={inputClass}
              name="phone"
              defaultValue={user.phone ?? ""}
              type="tel"
              maxLength={32}
              autoComplete="tel"
            />
          </span>
        </Field>
        <Button type="submit" className={styles.primary}>
          <Save aria-hidden="true" />
          {t.save}
        </Button>
      </fieldset>
      {mutation.isError && <Failure error={mutation.error} />}
      {mutation.isSuccess && <p role="status">{t.saved}</p>}
    </form>
  );
}
function Avatar({ user }: { user: User }) {
  const cache = useQueryClient();
  const mutation = useMutation({
    mutationFn: readerApi.avatar,
    onSuccess: async (data) => {
      cache.setQueryData(["profile"], data);
      await checkSession();
    },
  });
  return (
    <section className={styles.card} aria-labelledby="profile-photo-title">
      <header className={styles.cardHeading}>
        <span className={styles.badge}>
          <ImageIcon aria-hidden="true" />
        </span>
        <h2 id="profile-photo-title">{t.avatar}</h2>
      </header>
      <div className={styles.photoBody}>
        <div className={styles.avatar}>
          {user.avatar_url ? (
            <Image
              src={user.avatar_url}
              width={120}
              height={120}
              unoptimized
              className={styles.avatarImage}
              alt={t.avatar}
            />
          ) : (
            <div aria-label={t.avatar} className={styles.initials}>
              {user.first_name[0]}
              {user.last_name[0]}
            </div>
          )}
          <span className={styles.camera} aria-hidden="true">
            <Camera />
          </span>
        </div>
        <div className={styles.photoControls}>
          <p id="profile-image-hint" className={styles.hint}>
            {t.imageHint}
          </p>
          <form
            className={styles.photoForm}
            onSubmit={(e) => {
              e.preventDefault();
              const file = new FormData(e.currentTarget).get("file");
              if (file instanceof File && file.size) mutation.mutate(file);
            }}
          >
            <input
              aria-label={t.avatar}
              aria-describedby="profile-image-hint"
              name="file"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              required
              disabled={mutation.isPending}
            />
            <Button
              type="submit"
              className={styles.primary}
              disabled={mutation.isPending}
            >
              <Upload aria-hidden="true" />
              {t.upload}
            </Button>
            <Button
              type="button"
              variant="outline"
              className={styles.secondary}
              disabled={mutation.isPending || !user.avatar_url}
              onClick={() => {
                if (window.confirm(t.confirmRemove)) mutation.mutate(null);
              }}
            >
              <Trash2 aria-hidden="true" />
              {t.removeAvatar}
            </Button>
          </form>
        </div>
      </div>
      {mutation.isError && <Failure error={mutation.error} />}
      {mutation.isSuccess && <p role="status">{t.saved}</p>}
    </section>
  );
}
function PreferenceForm({ initial }: { initial: Preferences }) {
  const [selected, setSelected] = useState<Reference[]>(initial.categories);
  const cache = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => readerApi.savePreferences(selected.map((row) => row.id)),
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["preferences"] });
      await cache.invalidateQueries({ queryKey: ["recommendations"] });
    },
  });
  return (
    <fieldset disabled={mutation.isPending} className={styles.preferences}>
      <p className={styles.hint}>{t.optional}</p>
      <ReferencePicker
        kind="categories"
        selected={selected}
        onChange={(rows) => {
          if (rows.length <= 30) setSelected(rows);
        }}
      />
      <Button
        className={styles.primary}
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        <Save aria-hidden="true" />
        {t.save}
      </Button>
      {mutation.isError && <Failure error={mutation.error} />}
      {mutation.isSuccess && <p role="status">{t.saved}</p>}
    </fieldset>
  );
}
function Interests() {
  const result = useQuery({
    queryKey: ["preferences"],
    queryFn: readerApi.preferences,
  });
  return (
    <section className={styles.card} aria-labelledby="profile-interests-title">
      <header className={styles.cardHeading}>
        <span className={styles.badge}>
          <Star aria-hidden="true" />
        </span>
        <h2 id="profile-interests-title">{t.preferences}</h2>
      </header>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <PreferenceForm initial={result.data} />
      )}
    </section>
  );
}
export function Profile() {
  const result = useQuery({
    queryKey: ["profile"],
    queryFn: readerApi.profile,
  });
  return (
    <div className={styles.profile}>
      <CatalogShell title={t.profile}>
        <ProfileHero />
        <div className={styles.content}>
          {result.isPending ? (
            <p role="status">{t.loading}</p>
          ) : result.isError ? (
            <Failure error={result.error} retry={() => void result.refetch()} />
          ) : (
            <div className={styles.columns}>
              <div className={styles.mainColumn}>
                <Avatar user={result.data} />
                <section
                  className={styles.card}
                  aria-labelledby="profile-info-title"
                >
                  <header className={styles.cardHeading}>
                    <span className={styles.badge}>
                      <UserRound aria-hidden="true" />
                    </span>
                    <div>
                      <h2 id="profile-info-title">Жеке мәліметтер</h2>
                      <p>Есептік жазбаңыздың негізгі ақпаратын жаңартыңыз.</p>
                    </div>
                  </header>
                  <ProfileForm user={result.data} />
                </section>
                {result.data.role === "READER" && <Interests />}
              </div>
              <aside className={styles.sidebar}>
                <div className={styles.sidebarCard}>
                  <section className={styles.infoCard} aria-label="Email">
                    <div className={styles.infoHeading}>
                      <span className={styles.smallBadge}>
                        <Mail aria-hidden="true" />
                      </span>
                      <p className={styles.email}>
                        {t.email}: {result.data.email}
                      </p>
                    </div>
                    <p>{t.emailPolicy}</p>
                  </section>
                  <section
                    className={styles.infoCard}
                    aria-labelledby="profile-security-title"
                  >
                    <div className={styles.infoHeading}>
                      <span className={styles.smallBadge}>
                        <ShieldCheck aria-hidden="true" />
                      </span>
                      <h2 id="profile-security-title">Қауіпсіздік</h2>
                    </div>
                    <p>
                      Құпиясөз және сеанстар парақшасында құпиясөзіңізді
                      өзгертіп, белсенді сеанстарды басқаруға болады.
                    </p>
                    <Link
                      className={styles.securityLink}
                      href="/account/security"
                    >
                      {t.security}
                      <ArrowRight aria-hidden="true" />
                    </Link>
                  </section>
                </div>
                <div className={styles.supportCard}>
                  <div className={styles.infoHeading}>
                    <span className={styles.smallBadge}>
                      <BookOpen aria-hidden="true" />
                    </span>
                    <h2>Кітаптар әлемі әрқашан сізбен!</h2>
                  </div>
                  <p>
                    Жеке кабинетіңізді жаңартып, оқу тәжірибеңізді одан да
                    ыңғайлы етіңіз.
                  </p>
                  <span className={styles.accentLine} aria-hidden="true" />
                </div>
              </aside>
            </div>
          )}
        </div>
      </CatalogShell>
    </div>
  );
}
