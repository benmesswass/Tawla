/**
 * Politique de confidentialité (Phase 16).
 *
 * Séparée des dictionnaires du parcours de commande : c'est un texte juridique
 * qui se relit en entier, pas une série de libellés d'interface. Toute
 * évolution du traitement des données (nouveau champ collecté, nouvelle durée
 * de conservation) doit passer ici — une politique qui ne décrit plus ce que
 * le code fait est pire que pas de politique.
 *
 * Ce texte ne décrit QUE ce que le code fait réellement aujourd'hui. Ne rien y
 * ajouter qui ne soit pas vérifiable dans le dépôt.
 */

const UPDATED_AT = { fr: "13 août 2026", ar: "13 أوت 2026" };

type Section = { title: string; paragraphs: string[] };
type PrivacyPage = {
  dir: "ltr" | "rtl";
  title: string;
  intro: string;
  updatedAt: string;
  sections: Section[];
  backToMenu: string;
};

const fr: PrivacyPage = {
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

const ar: PrivacyPage = {
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

export const PRIVACY: Record<string, PrivacyPage> = { fr, ar };
