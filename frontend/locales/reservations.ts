export const reservations = {
  title: "Менің броньдарым",
  detail: "Бронь туралы",
  reserve: "Кітапты брондау",
  wait: "Кезекке тұру",
  login: "Брондау үшін кіріңіз",
  cancel: "Броньнан бас тарту",
  confirm:
    "Броньнан бас тартасыз ба? Дайын дана кезектегі келесі оқырманға беріледі.",
  empty: "Әзірге броньдарыңыз жоқ.",
  all: "Барлығы",
  number: "Бронь нөмірі",
  created: "Брондалған уақыт",
  createdReady: "Кітап брондалды. Алуға дайын.",
  createdWaiting: "Күту кезегіне қосылдыңыз.",
  expires: "Алу мерзімі",
  position: "Кезектегі орын",
  queueNote:
    "Кезек брондау уақытымен реттеледі. Кітап алуға құқығы уақытша шектелген оқырман кезекте қалады.",
  pickup:
    "QR кодты кітапханашыға көрсетіңіз. Кітапты кітапханашы тексергеннен кейін береді.",
  qr: "Броньдің QR коды",
  showQR: "QR кодты көрсету",
  hideQR: "QR кодты жасыру",
  qrPrivate: "QR кодты басқа адамдармен бөліспеңіз.",
  expired: "Алу мерзімі аяқталды. QR жарамсыз.",
  cancelled: "Броньнан бас тартылды.",
  status: "Күйі",
  loading: "Жүктелуде…",
  states: {
    WAITING: "Кезекте",
    READY: "Алуға дайын",
    COMPLETED: "Аяқталған",
    CANCELLED: "Бас тартылған",
    EXPIRED: "Мерзімі аяқталған",
  },
};
export const reservationErrors: Record<string, string> = {
  RESERVATION_ALREADY_EXISTS:
    "Бұл кітапқа белсенді броніңіз бар. Менің броньдарым бетін ашыңыз.",
  RESERVATION_NOT_FOUND: "Бронь табылмады.",
  RESERVATION_NOT_READY: "Бұл бронь үшін QR қолжетімсіз.",
  RESERVATION_EXPIRED: "Бронь мерзімі аяқталған.",
  RESERVATION_ALREADY_COMPLETED: "Кітап берілген, бронь аяқталған.",
  RESERVATION_QUEUE_CONFLICT: "Бронь күйін кітапханашымен тексеріңіз.",
  USER_HAS_OVERDUE_BOOKS: "Алдымен мерзімі өткен кітаптарды қайтарыңыз.",
  QR_SERVICE_UNAVAILABLE:
    "QR қызметі уақытша қолжетімсіз. Кейінірек қайталаңыз.",
  SETTINGS_UNAVAILABLE: "Кітапхана баптаулары уақытша қолжетімсіз.",
};
