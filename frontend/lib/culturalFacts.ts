// Anecdotes culturelles affichées pendant l'attente cuisine (voir
// menu/[qrToken]/page.tsx) — un petit plus pendant les 10-20 minutes
// d'attente, plutôt qu'un écran silencieux. Faits vérifiés (UNESCO,
// géographie, traditions), pas de contenu spécifique à un plat précis du
// menu (celui-ci variant d'un restaurant à l'autre).
export const CULTURAL_FACTS: Record<"fr" | "ar", string[]> = {
  fr: [
    "Le couscous est inscrit au patrimoine culturel immatériel de l'UNESCO depuis 2020, une tradition partagée par l'Algérie, le Maroc, la Mauritanie et la Tunisie.",
    "La harissa tunisienne est elle-même reconnue par l'UNESCO depuis 2022 comme patrimoine culturel immatériel de l'humanité.",
    "Servir le thé à la menthe est un rituel d'hospitalité en Tunisie — le refuser peut être perçu comme un manque de politesse envers son hôte.",
    "Le brik, cette fine feuille croustillante à l'œuf, est un classique incontournable des tables tunisiennes pendant le Ramadan.",
    "Le tajine tunisien n'a rien à voir avec le plat mijoté marocain du même nom : c'est une sorte de quiche épaisse à base d'œufs, souvent servie froide.",
    "L'huile d'olive tunisienne compte parmi les plus anciennes traditions agricoles du pays, avec des oliviers cultivés depuis l'Antiquité.",
    "Le lablabi, une soupe de pois chiches épicée servie avec du pain rassis, est un plat populaire souvent pris au petit-déjeuner.",
    "La Tunisie est l'un des plus grands producteurs de dattes au monde, notamment la variété Deglet Nour, surnommée « doigt de lumière ».",
  ],
  ar: [
    "الكسكسي مسجل فالتراث الثقافي اللامادي لليونسكو من 2020 — تقليد نتقاسموه مع الجزائر والمغرب وموريتانيا.",
    "الهريسة التونسية زادة مسجلة عند اليونسكو من 2022 كتراث ثقافي لامادي للإنسانية.",
    "تقديم أتاي بالنعناع عادة تونسية أصيلة فالضيافة — رفضه يتحسب قلة أدب مع إلي عزمك.",
    "البريك، الورقة القرمشة بالعظمة، أكلة ما تنقصش من مائدة رمضان فتونس.",
    "التاجين التونسي ما عندوش علاقة بالطاجين المغربي — عندنا هو أكلة بالعظمة تشبه الكيش، وتتاكل بارة.",
    "زيت الزيتون التونسي من أقدم التقاليد الفلاحية فالبلاد، بزيتون مغروس من العصور القديمة.",
    "اللبلابي، شربة الحمص الحارة بالخبز اليابس، أكلة شعبية تتاكل حتى فطور الصباح.",
    "تونس من أكبر منتجي التمر فالعالم، خصوصا صنف « دقلة النور » إلي معناها « صباع النور ».",
  ],
};
