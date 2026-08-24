import { currentMarket } from "@/lib/market";

/**
 * Politique de confidentialité (Phase 16 ; réécriture RGPD F5, MARCHE_FRANCE.md
 * §3.1(2)).
 *
 * Séparée des dictionnaires du parcours de commande : c'est un texte juridique
 * qui se relit en entier, pas une série de libellés d'interface. Toute
 * évolution du traitement des données (nouveau champ collecté, nouvelle durée
 * de conservation) doit passer ici — une politique qui ne décrit plus ce que
 * le code fait est pire que pas de politique.
 *
 * Ce texte ne décrit QUE ce que le code fait réellement aujourd'hui. Ne rien y
 * ajouter qui ne soit pas vérifiable dans le dépôt.
 *
 * Deux droits, PAS deux traductions du même texte : la loi tunisienne
 * (n° 2004-63, INPDP) et le RGPD n'ouvrent pas les mêmes droits (le RGPD
 * ajoute portabilité et opposition, absentes de la version tunisienne) — le
 * marché du déploiement (`currentMarket()`, jamais une bascule par requête,
 * même principe que le halal par défaut F5-A6) décide donc du texte entier,
 * pas seulement de sa langue. `getPrivacyPage()` est le seul point d'entrée.
 *
 * Volontairement laissé en suspens côté France, marqué [[À COMPLÉTER]] dans
 * le texte plutôt qu'inventé : l'identité du responsable de traitement (quelle
 * structure juridique — F2, MARCHE_FRANCE.md ligne 585, micro-entreprise/SASU
 * non tranché) et son adresse de contact (le domaine français lui-même n'est
 * pas réservé, voir Annexe C4). Ni l'un ni l'autre ne se devinent depuis une
 * session de code — à remplir avant toute mise en ligne réelle en France,
 * avec l'expert-comptable (F2) et après réservation du domaine (F0, note sur
 * "MyTable").
 */

const UPDATED_AT = { fr: "13 août 2026", ar: "13 أوت 2026", fr_fr: "24 août 2026", en_fr: "24 August 2026" };

type Section = { title: string; paragraphs: string[] };
type PrivacyPage = {
  dir: "ltr" | "rtl";
  title: string;
  intro: string;
  updatedAt: string;
  sections: Section[];
  backToMenu: string;
};

const fr_tn: PrivacyPage = {
  dir: "ltr",
  title: "Politique de confidentialité",
  intro:
    "Tawla est le service de commande par QR code utilisé par le restaurant où vous êtes. Cette page dit exactement quelles données vous concernant sont enregistrées, pourquoi, combien de temps, et comment les faire supprimer.",
  updatedAt: `Dernière mise à jour : ${UPDATED_AT.fr}`,
  sections: [
    {
      title: "Qui traite vos données",
      paragraphs: [
        "Le restaurant dans lequel vous commandez est responsable des données que vous lui confiez. Tawla les héberge et les traite pour son compte, et ne s'en sert pour aucune autre finalité.",
        "Aucun compte client n'existe dans Tawla : vous commandez en scannant le QR de votre table, sans inscription ni mot de passe.",
      ],
    },
    {
      title: "Ce qui est enregistré",
      paragraphs: [
        "Votre commande : les plats choisis, les quantités, vos notes éventuelles pour la cuisine, la table, l'heure et le montant. C'est ce qui permet de vous servir et au restaurant de tenir sa comptabilité.",
        "Votre numéro de téléphone, uniquement si vous l'entrez vous-même pour la carte de fidélité. Le champ est facultatif : vous pouvez commander sans le remplir.",
        "Votre date de naissance, uniquement si vous l'entrez vous-même, et uniquement pour la réduction d'anniversaire. Le champ est facultatif.",
        "Un identifiant de notification, uniquement si vous acceptez d'être prévenu quand votre commande est prête. Il désigne votre navigateur, pas vous.",
      ],
    },
    {
      title: "Ce qui n'est jamais enregistré",
      paragraphs: [
        "Aucune donnée bancaire n'est saisie ni conservée dans Tawla.",
        "Ni votre nom, ni votre adresse, ni votre e-mail, ni votre position ne sont demandés.",
        "Vos données ne sont ni vendues, ni louées, ni transmises à un annonceur, ni utilisées pour vous démarcher.",
        "Le restaurant où vous commandez ne voit que ses propres commandes : votre numéro n'est pas partagé avec les autres établissements utilisant Tawla.",
      ],
    },
    {
      title: "Combien de temps",
      paragraphs: [
        "L'identifiant de notification est effacé dès que votre commande est servie ou annulée : il n'a plus rien à vous annoncer.",
        "Votre fiche de fidélité (numéro de téléphone et date de naissance) est supprimée après 24 mois sans nouvelle commande.",
        "Les commandes sont conservées par le restaurant pour sa comptabilité et son suivi d'activité.",
        "Si vous êtes sur un établissement de démonstration — le bandeau en haut de l'écran vous le dit —, tout ce qu'il contient est supprimé deux heures après son ouverture : les commandes, les tables et les comptes, sans exception et sans archive.",
      ],
    },
    {
      title: "Vos droits",
      paragraphs: [
        "Vous pouvez demander à consulter, corriger ou supprimer les données vous concernant. Demandez-le au restaurant, ou écrivez à contact@tawla.tn en indiquant le numéro de téléphone concerné et le nom de l'établissement.",
        "La suppression est réelle : la fiche est effacée de la base, pas simplement masquée.",
        "Le traitement des données personnelles en Tunisie est encadré par la loi organique n° 2004-63 du 27 juillet 2004. Vous pouvez saisir l'Instance Nationale de Protection des Données Personnelles (INPDP) si vous estimez que vos droits ne sont pas respectés.",
      ],
    },
  ],
  backToMenu: "Retour",
};

const ar_tn: PrivacyPage = {
  dir: "rtl",
  title: "سياسة الخصوصية",
  intro:
    "Tawla هي خدمة الطلب بالـQR code إلي يستعملها المطعم إلي راك فيه. هذي الصفحة تقلك بالضبط شنوة المعطيات إلي تتسجل عليك، علاش، قداش تتعمر، وكيفاش تنجم تمسحها.",
  updatedAt: `آخر تحديث : ${UPDATED_AT.ar}`,
  sections: [
    {
      title: "شكون إلي يتصرف في معطياتك",
      paragraphs: [
        "المطعم إلي تطلب فيه هو المسؤول على المعطيات إلي تعطيهالو. Tawla تخزنهم وتعالجهم بالنيابة عليه، وما تستعملهمش لأي حاجة أخرى.",
        "ما فماش حساب زبون في Tawla : تطلب بالـQR تاع الطاولة، بلا تسجيل وبلا كلمة سر.",
      ],
    },
    {
      title: "شنوة إلي يتسجل",
      paragraphs: [
        "الطلبية تاعك : الماكلة إلي اخترتها، الكمية، الملاحظات للمطبخ، الطاولة، الوقت والمبلغ. هذا إلي يخلي المطعم يخدمك ويعمل حسابياتو.",
        "رقم التليفون تاعك، كان إذا كتبتو أنت روحك لبطاقة الولاء. الخانة إختيارية : تنجم تطلب بلاش ما تعمرها.",
        "تاريخ ميلادك، كان إذا كتبتو أنت روحك، وكان للتخفيض تاع عيد ميلادك. الخانة إختيارية.",
        "معرّف إشعار، كان إذا قبلت باش نعرفوك وقتلي الطلبية تكون لاهية. هذا المعرّف يخص المتصفح تاعك، موش أنت.",
      ],
    },
    {
      title: "شنوة إلي عمرو ما يتسجل",
      paragraphs: [
        "حتى معطيات بنكية ما تتكتبش وما تتخزنش في Tawla.",
        "لا إسمك، لا عنوانك، لا الإيميل تاعك، لا موقعك — ما يتطلبو منك حتى واحد منهم.",
        "معطياتك ما تتباعش، ما تتكراش، ما تتبعثش لمشهر، وما تتستعملش باش يعيطولك.",
        "المطعم إلي تطلب فيه ما يشوف كان الطلبيات متاعو : رقمك ما يتشاركش مع المطاعم الأخرى إلي تستعمل Tawla.",
      ],
    },
    {
      title: "قداش تتعمر",
      paragraphs: [
        "معرّف الإشعار يتمسح ديراكت كي الطلبية تتقدملك ولا تتلغى : ما بقاش عندو شنوة يقلك.",
        "بطاقة الولاء تاعك (رقم التليفون وتاريخ الميلاد) تتمسح بعد 24 شهر بلا طلبية جديدة.",
        "الطلبيات يحافظ عليهم المطعم للحسابيات ومتابعة النشاط.",
        "كان راك في محل تجريبي — الشريط إلي فوق الشاشة يقلك — كل شي فيه يتمسح بعد ساعتين من فتحو : الطلبيات، الطاولات والحسابات، الكل بلا استثناء وبلا أرشيف.",
      ],
    },
    {
      title: "حقوقك",
      paragraphs: [
        "تنجم تطلب تشوف، تصلّح ولا تمسح المعطيات إلي تخصك. أطلبها من المطعم، ولا أكتب لـcontact@tawla.tn وحط رقم التليفون المعني وإسم المحل.",
        "المسح حقيقي : البطاقة تتمسح من قاعدة المعطيات، موش كان تتخبى.",
        "معالجة المعطيات الشخصية في تونس ينظمها القانون الأساسي عدد 63 لسنة 2004 المؤرخ في 27 جويلية 2004. تنجم تلوج للهيئة الوطنية لحماية المعطيات الشخصية (INPDP) إذا شفت إلي حقوقك ما تحترمتش.",
      ],
    },
  ],
  backToMenu: "رجوع",
};

// --- Marché français (RGPD) -------------------------------------------------
//
// Mêmes traitements de données que la version tunisienne (le code ne change
// pas selon le marché) : commande, fidélité facultative, identifiant de
// notification, démo jetable. Ce qui change est le CADRE LÉGAL — RGPD plutôt
// que loi 2004-63 — donc les droits ouverts (portabilité, opposition,
// limitation : absents de la version tunisienne) et l'autorité de contrôle
// (CNIL plutôt qu'INPDP).

const fr_fr: PrivacyPage = {
  dir: "ltr",
  title: "Politique de confidentialité",
  intro:
    "Tawla est le service de commande par QR code utilisé par le restaurant où vous êtes. Cette page dit exactement quelles données vous concernant sont enregistrées, pourquoi, combien de temps, et comment exercer vos droits — conformément au Règlement général sur la protection des données (RGPD).",
  updatedAt: `Dernière mise à jour : ${UPDATED_AT.fr_fr}`,
  sections: [
    {
      title: "Qui traite vos données",
      paragraphs: [
        "Le restaurant dans lequel vous commandez est responsable du traitement (au sens de l'article 4 du RGPD) des données que vous lui confiez. Tawla agit comme sous-traitant : elle héberge et traite ces données pour le compte du restaurant, dans le cadre d'un contrat de sous-traitance (article 28 du RGPD), et ne s'en sert pour aucune autre finalité.",
        "Aucun compte client n'existe dans Tawla : vous commandez en scannant le QR de votre table, sans inscription ni mot de passe.",
        "[[À COMPLÉTER avant mise en ligne réelle — F2]] Coordonnées du responsable de traitement (raison sociale, forme juridique, adresse) et adresse de contact dédiée : non déterminées à ce stade (structure juridique française et nom de domaine non encore choisis).",
      ],
    },
    {
      title: "Ce qui est enregistré, et sur quelle base légale",
      paragraphs: [
        "Votre commande : les plats choisis, les quantités, vos notes éventuelles pour la cuisine, la table, l'heure et le montant — nécessaire à l'exécution du contrat qui vous lie au restaurant (article 6.1.b du RGPD).",
        "Votre numéro de téléphone et/ou votre date de naissance, uniquement si vous les saisissez vous-même pour le programme de fidélité — sur la base de votre consentement (article 6.1.a), que vous pouvez retirer à tout moment. Ces champs sont facultatifs : vous pouvez commander sans les remplir.",
        "Un identifiant de notification, uniquement si vous acceptez d'être prévenu quand votre commande est prête — sur la base de votre consentement. Il désigne votre navigateur, pas vous.",
      ],
    },
    {
      title: "Ce qui n'est jamais enregistré",
      paragraphs: [
        "Aucune donnée bancaire n'est saisie ni conservée dans Tawla.",
        "Ni votre nom, ni votre adresse, ni votre e-mail, ni votre position ne sont demandés.",
        "Vos données ne sont ni vendues, ni louées, ni transmises à un annonceur, ni utilisées pour vous démarcher.",
        "Le restaurant où vous commandez ne voit que ses propres commandes : votre numéro n'est pas partagé avec les autres établissements utilisant Tawla.",
      ],
    },
    {
      title: "Combien de temps",
      paragraphs: [
        "Conformément au principe de limitation de la conservation (article 5.1.e du RGPD), chaque donnée n'est gardée que le temps nécessaire à sa finalité.",
        "L'identifiant de notification est effacé dès que votre commande est servie ou annulée : il n'a plus rien à vous annoncer.",
        "Votre fiche de fidélité (numéro de téléphone et date de naissance) est supprimée après 24 mois sans nouvelle commande.",
        "Les commandes sont conservées par le restaurant pour sa comptabilité et son suivi d'activité.",
        "Si vous êtes sur un établissement de démonstration — le bandeau en haut de l'écran vous le dit —, tout ce qu'il contient est supprimé deux heures après son ouverture : les commandes, les tables et les comptes, sans exception et sans archive.",
      ],
    },
    {
      title: "Vos droits",
      paragraphs: [
        "Le RGPD vous donne le droit d'accéder à vos données, de les faire rectifier ou effacer, d'en limiter ou de vous opposer au traitement, et de les recevoir dans un format portable (articles 15 à 21 du RGPD). Pour la fidélité, vous pouvez aussi retirer votre consentement à tout moment.",
        "Demandez-le au restaurant, ou écrivez à [[À COMPLÉTER — adresse de contact non déterminée]] en indiquant le numéro de téléphone concerné et le nom de l'établissement.",
        "La suppression est réelle : la fiche est effacée de la base, pas simplement masquée.",
        "Si vous estimez que vos droits ne sont pas respectés, vous pouvez introduire une réclamation auprès de la Commission nationale de l'informatique et des libertés (CNIL) — cnil.fr.",
      ],
    },
  ],
  backToMenu: "Retour",
};

const en_fr: PrivacyPage = {
  dir: "ltr",
  title: "Privacy policy",
  intro:
    "Tawla is the QR-code ordering service used by the restaurant you're in. This page says exactly what data about you is recorded, why, for how long, and how to exercise your rights — in line with the EU General Data Protection Regulation (GDPR). The French version of this page is authoritative; this translation is provided for convenience.",
  updatedAt: `Last updated: ${UPDATED_AT.en_fr}`,
  sections: [
    {
      title: "Who processes your data",
      paragraphs: [
        "The restaurant where you order is the data controller (GDPR Article 4) for the data you share with it. Tawla acts as a processor: it hosts and processes this data on the restaurant's behalf, under a data processing agreement (GDPR Article 28), and never uses it for any other purpose.",
        "There is no customer account in Tawla: you order by scanning the QR code on your table, no sign-up or password required.",
        "[[TO BE COMPLETED before going live in France]] The data controller's registered details (legal name, structure, address) and a dedicated contact address are not yet determined (the French legal entity and domain name have not been finalized).",
      ],
    },
    {
      title: "What is recorded, and on what legal basis",
      paragraphs: [
        "Your order: the dishes chosen, quantities, any notes for the kitchen, the table, the time, and the amount — necessary for performing the contract between you and the restaurant (GDPR Article 6.1.b).",
        "Your phone number and/or date of birth, only if you enter them yourself for the loyalty programme — based on your consent (Article 6.1.a), which you can withdraw at any time. Both fields are optional: you can order without filling them in.",
        "A notification identifier, only if you agree to be notified when your order is ready — based on your consent. It identifies your browser, not you.",
      ],
    },
    {
      title: "What is never recorded",
      paragraphs: [
        "No banking data is ever entered or stored in Tawla.",
        "Your name, address, email, and location are never requested.",
        "Your data is never sold, rented, passed to advertisers, or used to contact you for marketing.",
        "The restaurant where you order only sees its own orders: your number is not shared with other establishments using Tawla.",
      ],
    },
    {
      title: "For how long",
      paragraphs: [
        "In line with the storage limitation principle (GDPR Article 5.1.e), each piece of data is kept only as long as needed for its purpose.",
        "The notification identifier is deleted as soon as your order is served or cancelled: it has nothing left to announce.",
        "Your loyalty record (phone number and date of birth) is deleted after 24 months without a new order.",
        "Orders are kept by the restaurant for its accounting and activity tracking.",
        "If you're on a demo establishment — the banner at the top of the screen tells you — everything it contains is deleted two hours after it was opened: orders, tables, and accounts, without exception and without archive.",
      ],
    },
    {
      title: "Your rights",
      paragraphs: [
        "The GDPR gives you the right to access your data, have it corrected or erased, restrict or object to its processing, and receive it in a portable format (GDPR Articles 15 to 21). For loyalty data, you can also withdraw your consent at any time.",
        "Ask the restaurant, or write to [[TO BE COMPLETED — contact address not yet determined]], stating the phone number concerned and the establishment's name.",
        "Deletion is real: the record is erased from the database, not just hidden.",
        "If you believe your rights are not being respected, you can lodge a complaint with the Commission nationale de l'informatique et des libertés (CNIL) — cnil.fr.",
      ],
    },
  ],
  backToMenu: "Back",
};

/**
 * Point d'entrée unique — jamais lire `PRIVACY_TN`/`PRIVACY_FR` directement :
 * le marché du déploiement décide du CADRE LÉGAL entier (voir commentaire
 * de fichier), la locale ne décide que de la langue à l'intérieur de ce cadre.
 */
export function getPrivacyPage(locale: string): PrivacyPage {
  if (currentMarket().code === "fr") {
    return locale === "en" ? en_fr : fr_fr;
  }
  return locale === "ar" ? ar_tn : fr_tn;
}
