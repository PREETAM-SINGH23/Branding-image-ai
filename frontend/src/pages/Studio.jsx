import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { clearToken, getToken } from "../auth.js";

const FORMAT_OPTIONS = [
  { key: "1080x1080", label: "Instagram Post (1080×1080)" },
  { key: "1080x1350", label: "Instagram Post (1080×1350)" },
  { key: "1080x1920", label: "Instagram Story (1080×1920)" },
];

const TAB_LABEL = {
  "1080x1080": "Square",
  "1080x1350": "Portrait",
  "1080x1920": "Story",
};

const TAB_ASPECT = {
  "1080x1080": "1 / 1",
  "1080x1350": "1080 / 1350",
  "1080x1920": "9 / 16",
};

/** Hero backgrounds: copies of files from repo ``assets/Sample-input-images`` (plus gradient / legacy stock). */
const SAMPLE_BACKGROUNDS = [
  { src: "/samples/asset-tata-hero.jpg", name: "asset-tata-hero.jpg", label: "Tata hero" },
  { src: "/samples/asset-vw-hero.jpg", name: "asset-vw-hero.jpg", label: "VW hero" },
  { src: "/samples/asset-brand-square.png", name: "asset-brand-square.png", label: "Brand square" },
  { src: "/samples/background-gradient.jpg", name: "background-gradient.jpg", label: "Gradient" },
  { src: "/samples/vehicle-blue.jpg", name: "vehicle-blue.jpg", label: "Stock blue" },
  { src: "/samples/vehicle-gold.jpg", name: "vehicle-gold.jpg", label: "Stock gold" },
  { src: "/samples/vehicle-silver.jpg", name: "vehicle-silver.jpg", label: "Stock silver" },
  { src: "/samples/vehicle-teal.jpg", name: "vehicle-teal.jpg", label: "Stock teal" },
  { src: "/samples/vehicle-tan.jpg", name: "vehicle-tan.jpg", label: "Stock tan" },
];

const SAMPLE_LOGO_BRAND = { src: "/samples/asset-brand-square.png", name: "asset-brand-square.png" };
/** Five logos from ``assets/Logos`` + Tata dealer panel — used when cycling logos across outputs. */
const SAMPLE_LOGO_BADGE_PACK = [
  { src: "/samples/asset-logo-dark.png", name: "asset-logo-dark.png" },
  { src: "/samples/asset-logo-light.png", name: "asset-logo-light.png" },
  { src: "/samples/asset-vw-logo.png", name: "asset-vw-logo.png" },
  { src: "/samples/asset-vw1-logo.png", name: "asset-vw1-logo.png" },
  { src: "/samples/asset-tata-dealer-logo.png", name: "asset-tata-dealer-logo.png" },
];
/** Random “Use sample logo” picks from brand + badges so each click can differ. */
const SAMPLE_LOGOS_FOR_RANDOM = [SAMPLE_LOGO_BRAND, ...SAMPLE_LOGO_BADGE_PACK];

const TEMPLATE_OPTIONS_CORE = [
  {
    value: "promo_split",
    label: "Promo split",
    hint: "Diagonal accent wedge, hero word, price disc, phone + CONTACT US (social sale style).",
  },
  {
    value: "visit_dealer",
    label: "Visit dealer",
    hint: "Full hero + navy diagonal footer with Visit, dealer name, address, phone, site (showroom card).",
  },
  {
    value: "dealer_bottom",
    label: "Dealership · bottom panel",
    hint: "Hero car on top, flat solid bottom panel for dealer info; logo top-right (classic showroom creative).",
  },
  {
    value: "dealer_left",
    label: "Dealership · left panel",
    hint: "Left column for name + contact, car hero on the right; logo top-left (good for wide/side-on shots).",
  },
  {
    value: "dealer_overlay",
    label: "Dealership · overlay",
    hint: "Full-bleed photo with a semi-transparent bottom band for text (premium look).",
  },
  {
    value: "dealer_minimal",
    label: "Dealership · minimal CTA",
    hint: "Thin bottom strip: phone + headline as CTA; logo top-right (high-end minimal).",
  },
  {
    value: "auto",
    label: "Dealership · auto layout",
    hint: "Picks bottom / left / overlay from your hero image (light sky → bottom panel; darker left → left panel; else overlay).",
  },
  {
    value: "brand_overlay",
    label: "Brand overlay (packaged template)",
    hint: "Full-bleed hero (upload / AI / gradient) plus dealership template.png from the database (footer + frame). Enable Additional assets. Demo paths: VW-Apple (Autobahn), TATA-North (Bellad).",
  },
];

const TEMPLATE_OPTION_HERO_BAND = {
  value: "hero_band",
  label: "Hero band (optional layout)",
  hint: "Top slogan bar + hero area + three-column footer (site / phone / dealer). Enable below to use this template.",
};

function cssGradientFromAccent(hex) {
  const h = (hex || "#f97316").trim();
  const ok = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(h);
  const x = ok && h.length === 4 ? `#${h[1]}${h[1]}${h[2]}${h[2]}${h[3]}${h[3]}` : ok ? h : "#f97316";
  const r = parseInt(x.slice(1, 3), 16);
  const g = parseInt(x.slice(3, 5), 16);
  const b = parseInt(x.slice(5, 7), 16);
  const r2 = Math.max(0, r - 55);
  const g2 = Math.max(0, g - 45);
  const b2 = Math.max(0, b - 40);
  return `linear-gradient(165deg, rgb(${Math.min(255, r + 40)},${Math.min(255, g + 35)},${Math.min(255, b + 50)}) 0%, rgb(${r2},${g2},${b2}) 100%)`;
}

function Card({ children, className = "" }) {
  return (
    <div className={`rounded-2xl border border-slate-200/80 bg-white ${className}`}>{children}</div>
  );
}

function StepBadge({ n }) {
  return (
    <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-accent text-sm font-bold text-white">
      {n}
    </span>
  );
}

export default function Studio() {
  const nav = useNavigate();
  const [accounts, setAccounts] = useState([]);
  const [accountId, setAccountId] = useState("");
  const [dealerships, setDealerships] = useState([]);
  const [selectedDealerIds, setSelectedDealerIds] = useState(() => new Set());
  const [logoEnabled, setLogoEnabled] = useState(true);
  const [extraAssets, setExtraAssets] = useState(false);
  const [logoFile, setLogoFile] = useState(null);
  const [bgFile, setBgFile] = useState(null);
  const [bgPreviewUrl, setBgPreviewUrl] = useState("");
  const [formats, setFormats] = useState(() => new Set(["1080x1080", "1080x1350", "1080x1920"]));
  const [headline, setHeadline] = useState("New car for");
  const [body, setBody] = useState(
    "Little tiny text of something that you can remove and put your own text in it. This is just a template."
  );
  const [promoWord, setPromoWord] = useState("SALE");
  const [priceDisplay, setPriceDisplay] = useState("$59,000");
  const [accentHex, setAccentHex] = useState("#f97316");
  const [creativeTemplate, setCreativeTemplate] = useState("promo_split");
  const [enableHeroBandTemplate, setEnableHeroBandTemplate] = useState(false);
  const [rotateSampleLogos, setRotateSampleLogos] = useState(false);
  const [aiGenerateBackground, setAiGenerateBackground] = useState(false);
  const [openaiImagesReady, setOpenaiImagesReady] = useState(false);
  const [busy, setBusy] = useState(false);

  const visibleTemplateOptions = useMemo(
    () => (enableHeroBandTemplate ? [...TEMPLATE_OPTIONS_CORE, TEMPLATE_OPTION_HERO_BAND] : TEMPLATE_OPTIONS_CORE),
    [enableHeroBandTemplate]
  );
  const [error, setError] = useState("");
  const [dragBg, setDragBg] = useState(false);

  const [jobId, setJobId] = useState(null);
  const [job, setJob] = useState(null);
  const [outputs, setOutputs] = useState([]);
  const [thumbById, setThumbById] = useState({});
  const [selectedOutIds, setSelectedOutIds] = useState(() => new Set());
  const [tabFormat, setTabFormat] = useState("1080x1080");
  const [logoPreviewUrl, setLogoPreviewUrl] = useState("");

  const blobUrls = useRef(new Set());
  const outputsLoadedForJob = useRef(null);

  const trackBlob = (url) => {
    blobUrls.current.add(url);
    return url;
  };

  const revokeBlobs = useCallback(() => {
    blobUrls.current.forEach((u) => URL.revokeObjectURL(u));
    blobUrls.current.clear();
    setThumbById({});
  }, []);

  useEffect(() => {
    return () => revokeBlobs();
  }, [revokeBlobs]);

  useEffect(() => {
    if (!getToken()) {
      nav("/login", { replace: true });
      return;
    }
    (async () => {
      try {
        const list = await api("/api/accounts");
        setAccounts(list);
        try {
          const h = await fetch("/api/health");
          if (h.ok) {
            const j = await h.json();
            setOpenaiImagesReady(Boolean(j.openai_images_configured));
          } else {
            setOpenaiImagesReady(false);
          }
        } catch {
          setOpenaiImagesReady(false);
        }
      } catch {
        nav("/login", { replace: true });
      }
    })();
  }, [nav]);

  useEffect(() => {
    if (accounts.length && !accountId) setAccountId(String(accounts[0].id));
  }, [accounts, accountId]);

  useEffect(() => {
    if (!accountId) return;
    (async () => {
      const list = await api(`/api/accounts/${accountId}/dealerships`);
      setDealerships(list);
      setSelectedDealerIds(new Set());
    })();
  }, [accountId]);

  useEffect(() => {
    if (!enableHeroBandTemplate && creativeTemplate === "hero_band") {
      setCreativeTemplate("promo_split");
    }
  }, [enableHeroBandTemplate, creativeTemplate]);

  useEffect(() => {
    const dealerIntroTemplates = new Set([
      "visit_dealer",
      "dealer_bottom",
      "dealer_left",
      "dealer_overlay",
      "auto",
    ]);
    if (!dealerIntroTemplates.has(creativeTemplate)) return;
    setHeadline((h) => (h.trim() === "New car for" ? "Visit" : h));
  }, [creativeTemplate]);

  useEffect(() => {
    if (!bgFile) {
      setBgPreviewUrl("");
      return;
    }
    const u = URL.createObjectURL(bgFile);
    setBgPreviewUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [bgFile]);

  useEffect(() => {
    if (!logoFile) {
      setLogoPreviewUrl("");
      return;
    }
    const u = URL.createObjectURL(logoFile);
    setLogoPreviewUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [logoFile]);

  const firstSelectedDealer = useMemo(() => {
    const ids = [...selectedDealerIds].sort((a, b) => a - b);
    if (!ids.length) return null;
    return dealerships.find((d) => d.id === ids[0]) || null;
  }, [dealerships, selectedDealerIds]);

  const sortedDealershipIds = useMemo(
    () => [...dealerships].sort((a, b) => a.id - b.id).map((d) => d.id),
    [dealerships]
  );

  async function loadUrlAsFile(url, filename) {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Could not load sample file");
    const blob = await res.blob();
    const type = blob.type || (filename.endsWith(".png") ? "image/png" : "image/jpeg");
    return new File([blob], filename, { type });
  }

  async function applySampleBackground(sample) {
    try {
      const f = await loadUrlAsFile(sample.src, sample.name);
      setBgFile(f);
      setAiGenerateBackground(false);
      setError("");
    } catch (e) {
      setError(e.message || "Failed to load sample background");
    }
  }

  async function applySampleLogo() {
    try {
      const pick = SAMPLE_LOGOS_FOR_RANDOM[Math.floor(Math.random() * SAMPLE_LOGOS_FOR_RANDOM.length)];
      const f = await loadUrlAsFile(pick.src, pick.name);
      setLogoFile(f);
      setLogoEnabled(true);
      setError("");
    } catch (e) {
      setError(e.message || "Failed to load sample logo");
    }
  }

  async function uploadLogoFilesAndCollectIds(files) {
    const ids = [];
    for (const f of files) {
      const fdLg = new FormData();
      fdLg.append("file", f);
      const upLg = await api("/api/uploads/logo", { method: "POST", body: fdLg });
      ids.push(upLg.file_id);
    }
    return ids;
  }

  function toggleDealer(id) {
    setSelectedDealerIds((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  function removeDealer(id) {
    setSelectedDealerIds((prev) => {
      const n = new Set(prev);
      n.delete(id);
      return n;
    });
  }

  function toggleFormat(key) {
    setFormats((prev) => {
      const n = new Set(prev);
      if (n.has(key)) n.delete(key);
      else n.add(key);
      return n;
    });
  }

  const loadOutputs = useCallback(
    async (jid) => {
      const list = await api(`/api/jobs/${jid}/outputs`);
      setOutputs(list);
      setSelectedOutIds(new Set(list.map((o) => o.id)));
      revokeBlobs();
      const token = getToken();
      const next = {};
      await Promise.all(
        list.map(async (o) => {
          const r = await fetch(o.url, { headers: { Authorization: `Bearer ${token}` } });
          if (!r.ok) return;
          const b = await r.blob();
          const url = trackBlob(URL.createObjectURL(b));
          next[o.id] = url;
        })
      );
      setThumbById(next);
    },
    [revokeBlobs]
  );

  useEffect(() => {
    if (!jobId) return;
    outputsLoadedForJob.current = null;
    let stop = false;
    let intervalId;

    async function tick() {
      if (stop) return;
      try {
        const j = await api(`/api/jobs/${jobId}`);
        if (stop) return;
        setJob(j);
        if (j.status === "completed" || j.status === "failed") {
          clearInterval(intervalId);
        }
      } catch {
        /* ignore */
      }
    }

    void tick();
    intervalId = setInterval(tick, 900);
    return () => {
      stop = true;
      clearInterval(intervalId);
    };
  }, [jobId]);

  useEffect(() => {
    if (!jobId || job?.status !== "completed") return;
    if (outputsLoadedForJob.current === jobId) return;
    outputsLoadedForJob.current = jobId;
    loadOutputs(jobId);
  }, [jobId, job?.status, loadOutputs]);

  async function submitCreativeJob(options = {}) {
    const dealershipIds = options.dealershipIds ?? [...selectedDealerIds];
    const formatList = options.formatList ?? [...formats];

    setError("");
    if (!accountId) {
      setError("Select an account.");
      return;
    }
    if (!dealershipIds.length) {
      setError("Select at least one dealership.");
      return;
    }
    if (!formatList.length) {
      setError("Select at least one output format.");
      return;
    }
    if (aiGenerateBackground && bgFile) {
      setError("Remove the uploaded background to use an AI-generated hero, or turn off AI hero.");
      return;
    }
    setBusy(true);
    try {
      let backgroundFileId = null;
      if (bgFile) {
        const fdBg = new FormData();
        fdBg.append("file", bgFile);
        const upBg = await api("/api/uploads/background", { method: "POST", body: fdBg });
        backgroundFileId = upBg.file_id;
      }

      const useRotation = Boolean(options.rotateSampleLogos);
      let logoFileId = null;
      let logoFileIds = null;
      if (logoEnabled) {
        if (useRotation) {
          const files = await Promise.all(
            SAMPLE_LOGO_BADGE_PACK.map((s) => loadUrlAsFile(s.src, s.name))
          );
          logoFileIds = await uploadLogoFilesAndCollectIds(files);
        } else if (logoFile) {
          const fdLg = new FormData();
          fdLg.append("file", logoFile);
          const upLg = await api("/api/uploads/logo", { method: "POST", body: fdLg });
          logoFileId = upLg.file_id;
        }
      }

      const jobBody = {
        account_id: Number(accountId),
        dealership_ids: dealershipIds,
        background_file_id: backgroundFileId,
        formats: formatList,
        logo_enabled: logoEnabled,
        logo_file_id: logoFileIds ? null : logoFileId,
        logo_file_ids: logoFileIds,
        extra_assets_enabled: extraAssets,
        headline: headline.trim() || null,
        body: body.trim() || null,
        promo_word: promoWord.trim() || null,
        price_display: priceDisplay.trim() || null,
        accent_hex: /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(accentHex.trim()) ? accentHex.trim() : null,
        creative_template: creativeTemplate,
        ai_generate_background: Boolean(aiGenerateBackground && !bgFile),
      };

      const created = await api("/api/jobs", {
        method: "POST",
        body: JSON.stringify(jobBody),
      });
      outputsLoadedForJob.current = null;
      setJobId(created.id);
      setJob(created);
      setOutputs([]);
      setThumbById({});
      setSelectedOutIds(new Set());
    } catch (e) {
      setError(e.message || "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleGenerate() {
    await submitCreativeJob({ rotateSampleLogos: logoEnabled && rotateSampleLogos });
  }

  async function generateFiveCreatives() {
    const ids = sortedDealershipIds.slice(0, 5);
    if (!ids.length) {
      setError("No dealerships for this account.");
      return;
    }
    setFormats(new Set(["1080x1080"]));
    setSelectedDealerIds(new Set(ids));
    await submitCreativeJob({
      dealershipIds: ids,
      formatList: ["1080x1080"],
      rotateSampleLogos: logoEnabled,
    });
  }

  async function generateFifteenCreatives() {
    const ids = sortedDealershipIds.slice(0, 5);
    if (sortedDealershipIds.length < 5) {
      setError(
        `Generate 15 needs five dealerships (5 × 3 formats = 15 files). This account has ${sortedDealershipIds.length}. Add dealers or use Generate 5.`
      );
      return;
    }
    const fl = ["1080x1080", "1080x1350", "1080x1920"];
    setFormats(new Set(fl));
    setSelectedDealerIds(new Set(ids));
    await submitCreativeJob({
      dealershipIds: ids,
      formatList: fl,
      rotateSampleLogos: logoEnabled,
    });
  }

  async function downloadZip(ids) {
    const res = await fetch(`/api/jobs/${jobId}/download-zip`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${getToken()}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(ids == null ? {} : { output_ids: ids }),
    });
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `creatives_job_${jobId}.zip`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const filteredOutputs = outputs.filter((o) => o.format_key === tabFormat);
  const accountName = accounts.find((a) => String(a.id) === String(accountId))?.name || "—";

  return (
    <div className="p-6 pb-12">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Create New Creatives</h1>
        <p className="mt-1 text-sm text-slate-600">Configure a bulk run, preview the first dealership, then download ZIPs.</p>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.15fr)_280px_minmax(300px,440px)] xl:items-start">
          <Card className="min-w-0 space-y-5 p-6 shadow-md">
            <div className="flex gap-3 border-b border-slate-100 pb-4">
              <StepBadge n={1} />
              <div className="min-w-0 flex-1">
                <h2 className="text-sm font-semibold text-slate-900">Select Account (Brand)</h2>
                <select
                  className="mt-2 w-full max-w-md rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none ring-accent focus:ring-2"
                  value={accountId}
                  onChange={(e) => setAccountId(e.target.value)}
                >
                  <option value="" disabled>
                    Choose…
                  </option>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex gap-3 border-b border-slate-100 pb-4">
              <StepBadge n={2} />
              <div className="min-w-0 flex-1">
                <h2 className="text-sm font-semibold text-slate-900">Select Dealerships</h2>
                <p className="mt-1 text-xs text-slate-500">
                  {selectedDealerIds.size} dealership{selectedDealerIds.size === 1 ? "" : "s"} selected
                </p>
                <div className="mt-2 flex min-h-[44px] flex-wrap gap-2 rounded-xl border border-slate-200 bg-slate-50 p-2">
                  {[...selectedDealerIds]
                    .sort((a, b) => a - b)
                    .map((id) => {
                      const d = dealerships.find((x) => x.id === id);
                      if (!d) return null;
                      return (
                        <span
                          key={id}
                          className="inline-flex items-center gap-1 rounded-full bg-accent/15 px-3 py-1 text-sm font-medium text-accent"
                        >
                          {d.name}
                          <button
                            type="button"
                            className="ml-0.5 rounded-full px-1.5 text-base leading-none text-accent hover:bg-accent/20"
                            onClick={() => removeDealer(id)}
                            aria-label={`Remove ${d.name}`}
                          >
                            ×
                          </button>
                        </span>
                      );
                    })}
                  {!selectedDealerIds.size && (
                    <span className="self-center text-sm text-slate-400">Pick dealers below…</span>
                  )}
                </div>
                <div className="mt-3 max-h-64 space-y-1 overflow-y-auto rounded-xl border border-slate-100 p-2">
                  {dealerships.map((d) => (
                    <label
                      key={d.id}
                      className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-50"
                    >
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-slate-300 text-accent focus:ring-accent"
                        checked={selectedDealerIds.has(d.id)}
                        onChange={() => toggleDealer(d.id)}
                      />
                      <span className="text-slate-700">{d.name}</span>
                    </label>
                  ))}
                  {!dealerships.length && <p className="text-sm text-slate-500">No dealerships for this account.</p>}
                </div>
              </div>
            </div>

            <div className="flex gap-3 border-b border-slate-100 pb-4">
              <StepBadge n={3} />
              <div className="min-w-0 flex-1 space-y-3">
                <h2 className="text-sm font-semibold text-slate-900">Select Logo / Assets (Optional)</h2>
                <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-slate-100 px-3 py-2">
                  <span className="text-sm text-slate-700">Enable Logo</span>
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-accent"
                    checked={logoEnabled}
                    onChange={(e) => setLogoEnabled(e.target.checked)}
                  />
                </label>
                {logoEnabled && (
                  <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-100 px-3 py-2.5">
                    <input
                      type="checkbox"
                      className="mt-0.5 h-4 w-4 rounded border-slate-300 text-accent"
                      checked={rotateSampleLogos}
                      onChange={(e) => setRotateSampleLogos(e.target.checked)}
                    />
                    <span className="min-w-0 text-sm text-slate-700">
                      <span className="font-medium text-slate-800">Different logo on each output</span>
                      <span className="mt-0.5 block text-xs text-slate-500">
                        Uses five built-in badge samples in order (cycles if you have more outputs). Turn off to use one
                        uploaded or random sample logo for every image.
                      </span>
                    </span>
                  </label>
                )}
                {logoEnabled && (
                  <div className="space-y-2">
                    {logoPreviewUrl && (
                      <div className="flex items-center gap-3">
                        <img
                          src={logoPreviewUrl}
                          alt=""
                          className="h-14 w-14 rounded-full border-2 border-slate-200 bg-white object-contain p-1 shadow-sm"
                        />
                        <div className="text-xs text-slate-600">
                          <div className="font-medium text-slate-800">{logoFile?.name || "Logo"}</div>
                          <button
                            type="button"
                            className="mt-1 text-accent hover:underline"
                            onClick={() => document.getElementById("logo-input")?.click()}
                          >
                            Change logo
                          </button>
                        </div>
                      </div>
                    )}
                    <input id="logo-input" type="file" accept="image/png,image/jpeg" className="hidden" onChange={(e) => setLogoFile(e.target.files?.[0] || null)} />
                    {!logoFile && (
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => document.getElementById("logo-input")?.click()}
                          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                        >
                          Upload logo
                        </button>
                        <button
                          type="button"
                          onClick={applySampleLogo}
                          className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-200"
                        >
                          Use sample logo
                        </button>
                      </div>
                    )}
                  </div>
                )}
                <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-slate-100 px-3 py-2">
                  <span className="text-sm text-slate-700">Enable Additional Assets</span>
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-accent"
                    checked={extraAssets}
                    onChange={(e) => setExtraAssets(e.target.checked)}
                  />
                </label>
              </div>
            </div>

            <div className="flex gap-3 border-b border-slate-100 pb-4">
              <StepBadge n={4} />
              <div className="min-w-0 flex-1 space-y-3">
                <h2 className="text-sm font-semibold text-slate-900">Design template</h2>
                <p className="text-xs text-slate-500">
                  Layouts are drawn in code from your copy and dealer data. You do not upload finished poster artwork as the
                  background.
                </p>
                <label className="flex max-w-lg cursor-pointer items-center justify-between gap-3 rounded-xl border border-slate-100 px-3 py-2.5">
                  <span className="text-sm text-slate-700">Show optional Hero band template</span>
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-accent focus:ring-accent"
                    checked={enableHeroBandTemplate}
                    onChange={(e) => setEnableHeroBandTemplate(e.target.checked)}
                  />
                </label>
                <p className="max-w-lg text-[11px] text-slate-500">
                  Hero band adds a top slogan bar and a three-column footer. Leave off to keep only <strong>Promo split</strong>{" "}
                  and <strong>Visit dealer</strong>.
                </p>
                <select
                  className="w-full max-w-lg rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none ring-accent focus:ring-2"
                  value={creativeTemplate}
                  onChange={(e) => setCreativeTemplate(e.target.value)}
                >
                  {visibleTemplateOptions.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
                <p className="max-w-lg text-xs text-slate-500">
                  {visibleTemplateOptions.find((t) => t.value === creativeTemplate)?.hint}
                </p>
              </div>
            </div>

            <div className="flex gap-3 border-b border-slate-100 pb-4">
              <StepBadge n={5} />
              <div className="min-w-0 flex-1 space-y-3">
                <h2 className="text-sm font-semibold text-slate-900">Background image (optional)</h2>
                <p className="text-xs text-slate-500">
                  If you skip this, the app uses a smooth gradient from your accent color so you can still export
                  description-driven creatives.
                </p>
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragBg(true);
                  }}
                  onDragLeave={() => setDragBg(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragBg(false);
                    const f = e.dataTransfer.files?.[0];
                    if (f && /image\/(jpeg|png)/i.test(f.type)) {
                      setBgFile(f);
                      setAiGenerateBackground(false);
                    }
                  }}
                  className={`rounded-2xl border-2 border-dashed px-4 py-8 text-center transition-colors ${
                    dragBg ? "border-accent bg-accent/5" : "border-slate-200 bg-slate-50/80"
                  }`}
                >
                  <input
                    type="file"
                    accept="image/png,image/jpeg"
                    className="hidden"
                    id="bg-input"
                    onChange={(e) => {
                      const f = e.target.files?.[0] || null;
                      setBgFile(f);
                      if (f) setAiGenerateBackground(false);
                    }}
                  />
                  <label htmlFor="bg-input" className="cursor-pointer text-sm text-slate-600">
                    <span className="font-semibold text-accent">Drag & drop</span> or click to upload (JPG / PNG)
                  </label>
                  {bgFile && (
                    <p className="mt-2 text-xs text-slate-500">
                      {bgFile.name} · {(bgFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  )}
                  {bgFile && (
                    <button
                      type="button"
                      onClick={() => setBgFile(null)}
                      className="mt-2 text-xs font-medium text-accent hover:underline"
                    >
                      Remove background (use gradient only)
                    </button>
                  )}
                </div>
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Sample backgrounds</p>
                  <div className="flex flex-wrap gap-2">
                    {SAMPLE_BACKGROUNDS.map((s) => (
                      <button
                        key={s.src}
                        type="button"
                        onClick={() => applySampleBackground(s)}
                        className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm hover:border-accent hover:text-accent"
                      >
                        {s.label ||
                          s.name.replace(/^background-/, "").replace(/\.(jpg|png|jpeg)$/i, "")}
                      </button>
                    ))}
                  </div>
                </div>
                <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-100 px-3 py-2.5">
                  <input
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 rounded border-slate-300 text-accent disabled:opacity-50"
                    checked={aiGenerateBackground}
                    disabled={!!bgFile}
                    onChange={(e) => setAiGenerateBackground(e.target.checked)}
                  />
                  <span className="min-w-0 text-sm text-slate-700">
                    <span className="font-medium text-slate-800">AI hero image (OpenAI Images)</span>
                    <span className="mt-0.5 block text-xs text-slate-500">
                      Optional. With no uploaded photo, each render calls OpenAI Images (e.g. DALL·E) for the hero background.
                      Set{" "}
                      <code className="rounded bg-slate-100 px-1 text-slate-800">OPENAI_API_KEY</code> in{" "}
                      <code className="rounded bg-slate-100 px-1 text-slate-800">backend/.env</code> and restart the API.
                      Otherwise you get the accent gradient.
                      {bgFile ? " Remove the uploaded background first." : ""}{" "}
                      {!openaiImagesReady && !bgFile ? (
                        <span className="text-slate-600"> No OpenAI key detected — AI hero will fall back to gradient.</span>
                      ) : null}
                    </span>
                  </span>
                </label>
              </div>
            </div>

            <div className="flex gap-3">
              <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-slate-200 text-sm font-bold text-slate-600">
                ✎
              </span>
              <div className="min-w-0 flex-1 space-y-2">
                <h2 className="text-sm font-semibold text-slate-900">Copy &amp; accent</h2>
                {creativeTemplate === "promo_split" && (
                  <p className="text-xs text-slate-500">
                    Diagonal wedge + hero word + price disc; phone and CONTACT US come from each dealership. Long
                    headline/body are trimmed to fit the wedge.
                  </p>
                )}
                {creativeTemplate === "visit_dealer" && (
                  <p className="text-xs text-slate-500">
                    Dealer name, address, phone, and website are pulled from each dealership record. Use headline for the
                    small word above the name (e.g. Visit).
                  </p>
                )}
                {["dealer_bottom", "dealer_left", "dealer_overlay"].includes(creativeTemplate) && (
                  <p className="text-xs text-slate-500">
                    Same dealer fields as Visit dealer. Headline is the small word above the dealer name (e.g. Visit). Accent
                    tints the panel color.
                  </p>
                )}
                {creativeTemplate === "dealer_minimal" && (
                  <p className="text-xs text-slate-500">
                    Phone comes from each dealership. Headline becomes the right-hand CTA line (default: schedule / visit
                    style).
                  </p>
                )}
                {creativeTemplate === "auto" && (
                  <p className="text-xs text-slate-500">
                    Upload a hero image for best results. The engine picks bottom panel, left panel, or overlay from simple
                    image analysis; headline behaves like Visit layouts when it resolves to those.
                  </p>
                )}
                {creativeTemplate === "hero_band" && (
                  <p className="text-xs text-slate-500">
                    Headline drives the top banner; body is a short tagline over the hero area. Footer columns use each
                    dealer&apos;s site, phone, name, and address.
                  </p>
                )}
                <input
                  className="w-full max-w-lg rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none ring-accent focus:ring-2"
                  placeholder={
                    ["visit_dealer", "dealer_bottom", "dealer_left", "dealer_overlay", "auto"].includes(creativeTemplate)
                      ? "Small intro (e.g. Visit)"
                      : creativeTemplate === "dealer_minimal"
                        ? "CTA line (e.g. SCHEDULE YOUR VISIT)"
                        : creativeTemplate === "hero_band"
                          ? "Top banner (e.g. CAR BUYING REDEFINED)"
                          : "Headline (e.g. New car for)"
                  }
                  value={headline}
                  onChange={(e) => setHeadline(e.target.value)}
                />
                {creativeTemplate === "promo_split" && (
                  <>
                    <input
                      className="w-full max-w-lg rounded-xl border border-slate-200 px-3 py-2 text-sm font-bold uppercase outline-none ring-accent focus:ring-2"
                      placeholder="Hero word (e.g. SALE)"
                      value={promoWord}
                      onChange={(e) => setPromoWord(e.target.value)}
                    />
                    <input
                      className="w-full max-w-lg rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none ring-accent focus:ring-2"
                      placeholder="Price in disc (e.g. $59,000)"
                      value={priceDisplay}
                      onChange={(e) => setPriceDisplay(e.target.value)}
                    />
                  </>
                )}
                <div className="flex max-w-lg flex-wrap items-center gap-2">
                  <label className="text-xs text-slate-500">Accent / gradient</label>
                  <input
                    type="color"
                    className="h-9 w-14 cursor-pointer rounded border border-slate-200 bg-white"
                    value={/^#([0-9a-fA-F]{6})$/.test(accentHex) ? accentHex : "#f97316"}
                    onChange={(e) => setAccentHex(e.target.value)}
                  />
                  <input
                    className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2 font-mono text-xs outline-none ring-accent focus:ring-2"
                    placeholder="#f97316"
                    value={accentHex}
                    onChange={(e) => setAccentHex(e.target.value)}
                  />
                </div>
                <textarea
                  className="w-full max-w-lg rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none ring-accent focus:ring-2"
                  rows={3}
                  placeholder={
                    creativeTemplate === "hero_band"
                      ? "Tagline over hero (optional)"
                      : "Supporting text (promo split) or notes"
                  }
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                />
              </div>
            </div>
          </Card>

          <Card className="flex min-h-0 flex-col p-6 shadow-md xl:sticky xl:top-6 xl:self-start">
            <h2 className="text-sm font-semibold text-slate-900">Summary</h2>
            <ul className="mt-4 space-y-3 text-sm">
              <li className="flex justify-between gap-2 border-b border-slate-100 pb-2">
                <span className="text-slate-500">Brand</span>
                <span className="font-medium text-slate-800">{accountName}</span>
              </li>
              <li className="flex justify-between gap-2 border-b border-slate-100 pb-2">
                <span className="text-slate-500">Dealerships</span>
                <span className="font-medium text-slate-800">{selectedDealerIds.size}</span>
              </li>
              <li className="flex justify-between gap-2 border-b border-slate-100 pb-2">
                <span className="text-slate-500">Logo</span>
                <span className="max-w-[120px] truncate text-right font-medium text-slate-800">
                  {logoEnabled ? logoFile?.name || "On (no file)" : "Off"}
                </span>
              </li>
              <li className="flex justify-between gap-2 border-b border-slate-100 pb-2">
                <span className="text-slate-500">Template</span>
                <span className="max-w-[140px] truncate text-right font-medium text-slate-800">
                  {visibleTemplateOptions.find((t) => t.value === creativeTemplate)?.label || creativeTemplate}
                </span>
              </li>
              <li className="flex justify-between gap-2 border-b border-slate-100 pb-2">
                <span className="text-slate-500">Background</span>
                <span className="max-w-[120px] truncate text-right font-medium text-slate-800">
                  {bgFile?.name || "Gradient only"}
                </span>
              </li>
              {creativeTemplate === "promo_split" && (
                <>
                  <li className="flex justify-between gap-2 border-b border-slate-100 pb-2">
                    <span className="text-slate-500">Hero</span>
                    <span className="max-w-[120px] truncate text-right font-bold text-slate-800">{promoWord || "SALE"}</span>
                  </li>
                  <li className="flex justify-between gap-2 pb-2">
                    <span className="text-slate-500">Price</span>
                    <span className="font-medium text-slate-800">{priceDisplay || "—"}</span>
                  </li>
                </>
              )}
            </ul>
            <div className="mt-6">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Output formats</h3>
              <div className="mt-2 space-y-2">
                {FORMAT_OPTIONS.map((f) => (
                  <label key={f.key} className="flex cursor-pointer items-start gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      className="mt-0.5 h-4 w-4 rounded border-slate-300 text-accent"
                      checked={formats.has(f.key)}
                      onChange={() => toggleFormat(f.key)}
                    />
                    <span>{f.label}</span>
                  </label>
                ))}
              </div>
            </div>
            <button
              type="button"
              disabled={busy}
              onClick={handleGenerate}
              className="mt-auto w-full rounded-xl bg-accent py-3 text-sm font-bold text-white shadow-md transition hover:bg-accent-hover disabled:opacity-60"
            >
              {busy ? "Starting…" : "Generate Creatives"}
            </button>
            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
              <button
                type="button"
                disabled={busy || sortedDealershipIds.length === 0}
                onClick={() => generateFiveCreatives()}
                className="rounded-xl border-2 border-accent bg-white py-2.5 text-xs font-bold text-accent transition hover:bg-accent/5 disabled:opacity-50"
              >
                Generate 5 creatives
              </button>
              <button
                type="button"
                disabled={busy || sortedDealershipIds.length < 5}
                title={
                  sortedDealershipIds.length < 5
                    ? "Need at least five dealerships on this account"
                    : "5 dealers × 3 formats"
                }
                onClick={() => generateFifteenCreatives()}
                className="rounded-xl border-2 border-slate-300 bg-slate-50 py-2.5 text-xs font-bold text-slate-800 transition hover:bg-slate-100 disabled:opacity-50"
              >
                Generate 15 creatives
              </button>
            </div>
            <p className="mt-2 text-[11px] leading-snug text-slate-500">
              <strong className="font-semibold text-slate-600">5</strong> = first five dealers × square post only
              {logoEnabled ? " (with logo on, five different sample badges cycle A→E across the five files)" : ""}.
              <strong className="font-semibold text-slate-600"> 15</strong> = those five dealers × all three formats (needs 5+ dealers
              {logoEnabled ? "; logos cycle through the same five samples" : ""}).
            </p>
            <p className="mt-2 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-[11px] text-slate-600">
              <span className="font-semibold text-slate-700">Copy:</span> headline and body are shortened in the server to fit
              the template (word-aware truncation). No external text services.
            </p>
            {selectedDealerIds.size === 1 && formats.size > 1 && (
              <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] leading-snug text-amber-950">
                <span className="font-semibold">Why do my files look the same?</span> With only{" "}
                <strong>one</strong> dealership selected, every output uses the same copy and dealer phone — only the{" "}
                <strong>aspect ratio</strong> changes (square vs portrait vs story). Choose{" "}
                <strong>multiple dealerships</strong> to get different contact blocks per image.
              </p>
            )}
          </Card>

        <Card className="min-w-0 p-6 shadow-md xl:sticky xl:top-6 xl:self-start">
          <h2 className="text-sm font-semibold text-slate-900">Preview</h2>
          <div className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-slate-900 shadow-inner">
            {firstSelectedDealer ? (
              <div className="relative aspect-square w-full bg-slate-800">
                {creativeTemplate === "promo_split" && (
                  <>
                    {bgPreviewUrl ? (
                      <img src={bgPreviewUrl} alt="" className="absolute inset-0 h-full w-full object-cover" />
                    ) : (
                      <div className="absolute inset-0" style={{ background: cssGradientFromAccent(accentHex) }} />
                    )}
                    <div
                      className="pointer-events-none absolute inset-0"
                      style={{
                        backgroundColor: /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(accentHex.trim())
                          ? accentHex.trim().length === 4
                            ? `#${accentHex[1]}${accentHex[1]}${accentHex[2]}${accentHex[2]}${accentHex[3]}${accentHex[3]}`
                            : accentHex.trim()
                          : "#f97316",
                        clipPath: "polygon(0 0, 100% 0, 0 100%)",
                      }}
                    />
                    {logoEnabled && logoPreviewUrl && (
                      <img
                        src={logoPreviewUrl}
                        alt=""
                        className="absolute right-3 top-3 z-20 w-[16%] max-w-[72px] rounded-full border-2 border-white/80 bg-white/90 object-contain p-0.5 shadow-lg"
                      />
                    )}
                    <div className="pointer-events-none absolute left-[5%] top-[5%] z-10 max-w-[48%]">
                      {headline && (
                        <div className="text-[13px] font-medium leading-snug text-white drop-shadow-sm">{headline}</div>
                      )}
                      {promoWord && (
                        <div className="mt-1 text-3xl font-black uppercase leading-[0.95] tracking-tight text-slate-900 drop-shadow-sm sm:text-4xl">
                          {promoWord}
                        </div>
                      )}
                      {body && (
                        <div className="mt-2 text-[10px] font-medium leading-snug text-white drop-shadow-md sm:text-[11px]">
                          {body}
                        </div>
                      )}
                      <div className="mt-3 inline-flex rounded-full bg-white px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-slate-900 shadow">
                        {accountName}
                      </div>
                    </div>
                    <div className="pointer-events-none absolute right-[10%] top-[32%] z-10 flex aspect-square w-[22%] max-w-[140px] items-center justify-center rounded-full bg-black text-center text-[10px] font-bold leading-tight text-white shadow-lg sm:text-xs">
                      {priceDisplay || "$59,000"}
                    </div>
                    <div className="pointer-events-none absolute bottom-[4.5%] left-[4%] right-[4%] z-10 flex gap-[3.5%]">
                      <div className="flex min-h-[38px] flex-1 items-center justify-center rounded-full bg-white px-2 text-[9px] font-semibold text-slate-900 shadow-md sm:text-[10px]">
                        <span className="mr-1 opacity-70" aria-hidden>
                          ☎
                        </span>
                        <span className="truncate">{firstSelectedDealer.phone || "—"}</span>
                      </div>
                      <div className="flex min-h-[38px] flex-[0.92] items-center justify-center rounded-full bg-black px-2 text-[9px] font-bold tracking-wide text-white shadow-md sm:text-[10px]">
                        CONTACT US
                      </div>
                    </div>
                  </>
                )}
                {creativeTemplate === "visit_dealer" && (
                  <>
                    {bgPreviewUrl ? (
                      <img src={bgPreviewUrl} alt="" className="absolute inset-0 h-full w-full object-cover" />
                    ) : (
                      <div className="absolute inset-0" style={{ background: cssGradientFromAccent(accentHex) }} />
                    )}
                    <div
                      className="pointer-events-none absolute inset-0 bg-[#121c34]"
                      style={{ clipPath: "polygon(0 56%, 0 100%, 100% 100%, 100% 66%)" }}
                    />
                    <div className="pointer-events-none absolute bottom-[6%] left-[6%] right-[8%] z-10 text-[10px] leading-snug text-white sm:text-[11px]">
                      <div className="opacity-90">{headline || "Visit"}</div>
                      <div className="text-sm font-bold sm:text-base">{firstSelectedDealer.name}</div>
                      <div className="mt-1 text-[9px] opacity-95">{firstSelectedDealer.address_line || "Address"}</div>
                      <div className="text-[9px]">{firstSelectedDealer.phone}</div>
                    </div>
                    {logoEnabled && logoPreviewUrl && (
                      <img
                        src={logoPreviewUrl}
                        alt=""
                        className="absolute right-3 top-3 z-20 w-[16%] max-w-[72px] rounded-full border border-white/70 bg-white/95 object-contain p-0.5 shadow-md"
                      />
                    )}
                  </>
                )}
                {(creativeTemplate === "dealer_bottom" || creativeTemplate === "auto") && (
                  <>
                    {bgPreviewUrl ? (
                      <img src={bgPreviewUrl} alt="" className="absolute inset-0 h-full w-full object-cover" />
                    ) : (
                      <div className="absolute inset-0" style={{ background: cssGradientFromAccent(accentHex) }} />
                    )}
                    <div className="pointer-events-none absolute inset-x-0 bottom-0 top-[58%] z-10 bg-slate-900" />
                    <div className="pointer-events-none absolute bottom-[5%] left-[6%] right-[10%] z-20 text-[10px] leading-snug text-white sm:text-[11px]">
                      <div className="opacity-90">{headline || "Visit"}</div>
                      <div className="text-sm font-bold sm:text-base">{firstSelectedDealer.name}</div>
                      <div className="mt-1 text-[9px] opacity-95">{firstSelectedDealer.address_line || "Address"}</div>
                      <div className="text-[9px]">{firstSelectedDealer.phone}</div>
                    </div>
                    {logoEnabled && logoPreviewUrl && (
                      <img
                        src={logoPreviewUrl}
                        alt=""
                        className="absolute right-3 top-3 z-20 w-[16%] max-w-[72px] rounded-full border border-white/70 bg-white/95 object-contain p-0.5 shadow-md"
                      />
                    )}
                    {creativeTemplate === "auto" && (
                      <div className="pointer-events-none absolute left-2 top-2 z-30 rounded-md bg-amber-500 px-2 py-1 text-[9px] font-bold uppercase tracking-wide text-white shadow">
                        Auto layout
                      </div>
                    )}
                  </>
                )}
                {creativeTemplate === "dealer_left" && (
                  <>
                    {bgPreviewUrl ? (
                      <img src={bgPreviewUrl} alt="" className="absolute inset-0 h-full w-full object-cover" />
                    ) : (
                      <div className="absolute inset-0" style={{ background: cssGradientFromAccent(accentHex) }} />
                    )}
                    <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-[38%] bg-slate-900" />
                    <div className="pointer-events-none absolute bottom-[8%] left-[4%] top-[10%] z-20 w-[32%] text-[9px] leading-snug text-white sm:text-[10px]">
                      <div className="opacity-90">{headline || "Visit"}</div>
                      <div className="mt-1 text-sm font-bold leading-tight sm:text-base">{firstSelectedDealer.name}</div>
                      <div className="mt-2 text-[8px] opacity-95">{firstSelectedDealer.address_line || "Address"}</div>
                      <div className="text-[8px]">{firstSelectedDealer.phone}</div>
                    </div>
                    {logoEnabled && logoPreviewUrl && (
                      <img
                        src={logoPreviewUrl}
                        alt=""
                        className="absolute left-3 top-3 z-20 w-[16%] max-w-[72px] rounded-full border border-white/70 bg-white/95 object-contain p-0.5 shadow-md"
                      />
                    )}
                  </>
                )}
                {creativeTemplate === "dealer_overlay" && (
                  <>
                    {bgPreviewUrl ? (
                      <img src={bgPreviewUrl} alt="" className="absolute inset-0 h-full w-full object-cover" />
                    ) : (
                      <div className="absolute inset-0" style={{ background: cssGradientFromAccent(accentHex) }} />
                    )}
                    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-[38%] bg-gradient-to-t from-slate-950/95 via-slate-950/70 to-transparent" />
                    <div className="pointer-events-none absolute bottom-[6%] left-[6%] right-[10%] z-20 text-[10px] leading-snug text-white sm:text-[11px]">
                      <div className="opacity-90">{headline || "Visit"}</div>
                      <div className="text-sm font-bold sm:text-base">{firstSelectedDealer.name}</div>
                      <div className="mt-1 text-[9px] opacity-95">{firstSelectedDealer.address_line || "Address"}</div>
                      <div className="text-[9px]">{firstSelectedDealer.phone}</div>
                    </div>
                    {logoEnabled && logoPreviewUrl && (
                      <img
                        src={logoPreviewUrl}
                        alt=""
                        className="absolute right-3 top-3 z-20 w-[16%] max-w-[72px] rounded-full border border-white/70 bg-white/95 object-contain p-0.5 shadow-md"
                      />
                    )}
                  </>
                )}
                {creativeTemplate === "dealer_minimal" && (
                  <>
                    {bgPreviewUrl ? (
                      <img src={bgPreviewUrl} alt="" className="absolute inset-0 h-full w-full object-cover" />
                    ) : (
                      <div className="absolute inset-0" style={{ background: cssGradientFromAccent(accentHex) }} />
                    )}
                    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-[10%] bg-black/95" />
                    <div className="pointer-events-none absolute bottom-[2.5%] left-[5%] z-20 text-[10px] font-bold text-white">
                      {firstSelectedDealer.phone || "—"}
                    </div>
                    <div className="pointer-events-none absolute bottom-[2.5%] right-[5%] z-20 max-w-[55%] text-right text-[9px] font-semibold uppercase tracking-wide text-slate-200">
                      {(headline || "SCHEDULE YOUR VISIT").slice(0, 28)}
                    </div>
                    {logoEnabled && logoPreviewUrl && (
                      <img
                        src={logoPreviewUrl}
                        alt=""
                        className="absolute right-3 top-3 z-20 w-[16%] max-w-[72px] rounded-full border border-white/70 bg-white/95 object-contain p-0.5 shadow-md"
                      />
                    )}
                  </>
                )}
                {creativeTemplate === "hero_band" && (
                  <div className="flex h-full w-full flex-col">
                    <div
                      className="flex h-[10%] shrink-0 items-center justify-center px-2 text-center text-[9px] font-bold uppercase tracking-wide leading-tight text-white sm:text-[10px]"
                      style={{
                        backgroundColor: /^#([0-9a-fA-F]{6})$/.test(accentHex.trim())
                          ? accentHex.trim()
                          : /^#([0-9a-fA-F]{3})$/.test(accentHex.trim())
                            ? `#${accentHex[1]}${accentHex[1]}${accentHex[2]}${accentHex[2]}${accentHex[3]}${accentHex[3]}`
                            : "#dc2626",
                      }}
                    >
                      {(headline || "CAR BUYING REDEFINED").slice(0, 42)}
                    </div>
                    <div className="relative min-h-0 flex-1">
                      {bgPreviewUrl ? (
                        <img src={bgPreviewUrl} alt="" className="h-full w-full object-cover" />
                      ) : (
                        <div className="h-full w-full" style={{ background: cssGradientFromAccent(accentHex) }} />
                      )}
                      {body && (
                        <p className="pointer-events-none absolute bottom-[26%] left-0 right-0 px-4 text-center text-[9px] font-medium text-white drop-shadow-md sm:text-[10px]">
                          {body.slice(0, 100)}
                          {body.length > 100 ? "…" : ""}
                        </p>
                      )}
                    </div>
                    <div className="flex h-[19%] shrink-0 text-[7px] sm:text-[8px]">
                      <div className="flex flex-[1.05] flex-col justify-center bg-gradient-to-r from-red-900 to-red-600 px-1.5 text-white">
                        <span className="truncate font-medium lowercase">
                          {(firstSelectedDealer.website || "www.yourdomain.com")
                            .replace(/^https?:\/\//i, "")
                            .split("/")[0]}
                        </span>
                      </div>
                      <div
                        className="flex flex-1 flex-col justify-center px-1.5 text-white"
                        style={{
                          background: /^#([0-9a-fA-F]{6})$/.test(accentHex.trim())
                            ? `linear-gradient(180deg, ${accentHex.trim()} 0%, ${accentHex.trim()}dd 100%)`
                            : "linear-gradient(180deg, #f87171 0%, #dc2626 100%)",
                        }}
                      >
                        <span className="italic opacity-95">Call or Text</span>
                        <span className="font-bold">{firstSelectedDealer.phone || "—"}</span>
                      </div>
                      <div className="relative flex flex-[1.1] flex-col justify-center overflow-hidden bg-[#e8e9ed] px-1.5 pl-3">
                        <span
                          className="absolute left-1 top-[14%] text-[10px] leading-none opacity-90"
                          style={{
                            color: /^#([0-9a-fA-F]{6})$/.test(accentHex.trim())
                              ? accentHex.trim()
                              : "#dc2626",
                          }}
                          aria-hidden
                        >
                          ▶
                        </span>
                        <span
                          className="text-[8px] font-bold uppercase leading-tight sm:text-[9px]"
                          style={{
                            color: /^#([0-9a-fA-F]{6})$/.test(accentHex.trim())
                              ? accentHex.trim()
                              : "#dc2626",
                          }}
                        >
                          {firstSelectedDealer.name.slice(0, 22)}
                        </span>
                        <span className="mt-0.5 truncate font-medium text-slate-800">
                          {(firstSelectedDealer.address_line || "").slice(0, 36)}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex aspect-square items-center justify-center p-6 text-center text-sm text-slate-400">
                Select at least one dealership to preview.
              </div>
            )}
          </div>
        </Card>
      </div>

      {jobId && job && (
        <Card className="mt-6 p-6 shadow-md">
          <h2 className="text-sm font-semibold text-slate-900">Generation progress</h2>
          <div className="mt-4">
            <div className="h-2.5 overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full rounded-full bg-accent transition-all"
                style={{ width: `${Math.min(100, job.progress_percent || 0)}%` }}
              />
            </div>
            <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-600">
              <span>
                Status: <strong className="text-accent">{job.status}</strong>
              </span>
              <span>
                Tasks: {job.completed_tasks}/{job.total_tasks}
              </span>
            </div>
            {job.error_message && <p className="mt-2 text-sm text-red-600">{job.error_message}</p>}
            {job.warning_message && (
              <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                {job.warning_message}
              </p>
            )}
          </div>
        </Card>
      )}

      {outputs.length > 0 && (
        <Card className="mt-6 p-6 shadow-md">
          <h2 className="text-sm font-semibold text-slate-900">Generated creatives</h2>
          {job?.warning_message && (
            <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              {job.warning_message}
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            {FORMAT_OPTIONS.filter((f) => formats.has(f.key)).map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setTabFormat(f.key)}
                className={`rounded-full border px-4 py-1.5 text-xs font-semibold transition ${
                  tabFormat === f.key
                    ? "border-accent bg-accent text-white"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => downloadZip(null)}
              className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover"
            >
              Download all (ZIP)
            </button>
            <button
              type="button"
              disabled={!selectedOutIds.size}
              onClick={() => downloadZip([...selectedOutIds])}
              className="rounded-xl border-2 border-accent bg-white px-4 py-2 text-sm font-semibold text-accent hover:bg-slate-50 disabled:opacity-40"
            >
              Download selected (ZIP)
            </button>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {filteredOutputs.map((o) => {
              const checked = selectedOutIds.has(o.id);
              return (
              <label
                key={o.id}
                className="group relative cursor-pointer overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm ring-slate-200 transition hover:ring-2 hover:ring-accent/25"
              >
                <input
                  type="checkbox"
                  className="absolute left-3 top-3 z-20 h-6 w-6 cursor-pointer opacity-0"
                  checked={checked}
                  onChange={() =>
                    setSelectedOutIds((prev) => {
                      const n = new Set(prev);
                      if (n.has(o.id)) n.delete(o.id);
                      else n.add(o.id);
                      return n;
                    })
                  }
                />
                <span
                  className={`pointer-events-none absolute left-3 top-3 z-10 flex h-6 w-6 items-center justify-center rounded-full border-2 border-white shadow-md ${
                    checked ? "bg-accent text-white" : "bg-white/95 text-slate-300"
                  }`}
                  aria-hidden
                >
                  {checked && (
                    <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                      <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </span>
                {thumbById[o.id] ? (
                  <img
                    src={thumbById[o.id]}
                    alt={o.dealership_name}
                    className="w-full object-cover"
                    style={{ aspectRatio: TAB_ASPECT[o.format_key] || "1 / 1" }}
                  />
                ) : (
                  <div className="flex aspect-square items-center justify-center text-xs text-slate-500">Loading…</div>
                )}
                <div className="border-t border-slate-200 bg-white px-2 py-1.5 text-center text-[11px] font-medium text-slate-700">
                  {o.dealership_name}
                </div>
              </label>
            );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
