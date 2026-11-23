import { useState, useEffect } from "react";
import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Activity, ShieldCheck, ChevronDown, ChevronUp } from "lucide-react";
import NotFound from "@/pages/not-found";
import NbaDashboardTab from "./NbaDashboardTab";
import {
  DEG3_OPTIONS,
  TENNIS_TOURS,
  type Deg3OptionKey,
  type TennisTourScope,
} from "./tennis-config";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
});

function Home() {
  const [activeTour, setActiveTour] = useState<TennisTourScope>(() => {
    try {
      const saved = window.localStorage.getItem("tennis_dashbord_tour_v2");
      if (saved === "ATP" || saved === "WTA" || saved === "ALL") return saved;
    } catch {}
    return "ATP";
  });

  const [deg3Opt, setDeg3Opt] = useState<Deg3OptionKey>(() => {
    try {
      const saved = window.localStorage.getItem("tennis_dashbord_deg3_v2");
      if (saved === "opt1" || saved === "opt2" || saved === "opt3") return saved;
    } catch {}
    return "opt3";
  });

  const [bench, setBench] = useState<any | null>(null);
  const [openDeg3Table, setOpenDeg3Table] = useState<boolean>(true);

  useEffect(() => {
    fetch("/tennis_deg3_benchmark.json")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) {
          setBench(d);
          try {
            const hasSaved = window.localStorage.getItem("tennis_dashbord_deg3_v2");
            if (!hasSaved && (d.bestDefaultOption === "opt1" || d.bestDefaultOption === "opt2" || d.bestDefaultOption === "opt3")) {
              setDeg3Opt(d.bestDefaultOption);
            }
          } catch {}
        }
      })
      .catch(() => {});
  }, []);

  const switchTour = (tour: TennisTourScope) => {
    setActiveTour(tour);
    try {
      window.localStorage.setItem("tennis_dashbord_tour_v2", tour);
    } catch {}
  };

  const switchDeg3 = (opt: Deg3OptionKey) => {
    setDeg3Opt(opt);
    try {
      window.localStorage.setItem("tennis_dashbord_deg3_v2", opt);
    } catch {}
  };

  const curOptMeta = DEG3_OPTIONS[deg3Opt];
  const curOptBench = bench?.options?.[deg3Opt]?.tours?.[activeTour];

  return (
    <div className="min-h-[100dvh] w-full bg-background flex flex-col font-sans">
      <div className="flex-1 w-full max-w-6xl mx-auto px-4 py-7 md:py-9 flex flex-col">
        <header className="mb-4 flex flex-wrap items-start justify-between gap-4" dir="rtl">
          <div>
            <div className="flex items-center gap-3 mb-1.5">
              <div className="h-10 w-10 rounded-lg bg-sky-700 text-white flex items-center justify-center shadow-sm">
                <Activity className="h-5 w-5" />
              </div>
              <h1
                className="text-lg md:text-2xl font-extrabold tracking-tight text-slate-900"
                data-testid="text-dashboard-title"
              >
                داشبورد پایه نجومی-جمتریا تنیس (TENNIS-SIGNAL-DASHBORD • ۲۰۲۴–۲۰۲۶)
              </h1>
            </div>
            <p className="text-slate-600 text-xs md:text-sm max-w-3xl leading-relaxed">
              محاسبات ۱۰۰٪ بدون آینده‌نگری (`r.date &lt; match.date`) بر پایه جمتریا نام بازیکن + ۳ آپشن `DEG3` مکان/تورنمنت + آسمان شهر مسابقه (`pyswisseph`) + قدرت ترکیبی Overall/Surface Elo (<b>مطلقاً بدون تاریخ تولد</b>).
            </p>
          </div>

          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs font-extrabold" dir="rtl">
            <ShieldCheck className="h-4 w-4 text-emerald-700" />
            ایزوله ۱۰۰٪ از شیت‌های NBA و NHL
          </div>
        </header>

        {/* Top-Level Tour Switcher (ATP / WTA / ALL) */}
        <div
          dir="rtl"
          className="mb-3 rounded-xl border-2 border-sky-300 bg-sky-50/90 p-2.5 shadow-xs flex flex-wrap items-center justify-between gap-2"
          data-testid="bar-tennis-tours"
        >
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid="tab-tour-atp"
              onClick={() => switchTour("ATP")}
              className={`px-3.5 py-2 rounded-lg text-xs font-extrabold transition-all ${
                activeTour === "ATP"
                  ? "bg-sky-700 text-white shadow-sm"
                  : "bg-white text-sky-950 hover:bg-sky-100 border border-sky-200"
              }`}
            >
              تور مردان ATP • جمتریا ۴۸۱ ➔ DEG1 = 121 (1° LEO • FIRE • KXATPMATCH)
            </button>
            <button
              type="button"
              data-testid="tab-tour-wta"
              onClick={() => switchTour("WTA")}
              className={`px-3.5 py-2 rounded-lg text-xs font-extrabold transition-all ${
                activeTour === "WTA"
                  ? "bg-emerald-700 text-white shadow-sm"
                  : "bg-white text-sky-950 hover:bg-sky-100 border border-sky-200"
              }`}
            >
              تور زنان WTA • جمتریا ۴۰۷ ➔ DEG1 = 47 (17° TAURUS • EARTH • KXWTAMATCH)
            </button>
            <button
              type="button"
              data-testid="tab-tour-all"
              onClick={() => switchTour("ALL")}
              className={`px-3.5 py-2 rounded-lg text-xs font-extrabold transition-all ${
                activeTour === "ALL"
                  ? "bg-indigo-700 text-white shadow-sm"
                  : "bg-white text-sky-950 hover:bg-sky-100 border border-sky-200"
              }`}
            >
              مجموع هر دو تور (ALL: ATP + WTA)
            </button>
          </div>
          <span className="px-2.5 py-1 rounded bg-white border border-sky-200 text-[11px] font-mono tabular-nums font-bold text-sky-900" dir="ltr">
            {activeTour === "ALL"
              ? `ALL TOURS • ATP(121) + WTA(47)`
              : `${activeTour} • DEG1=${TENNIS_TOURS[activeTour].deg1} (${TENNIS_TOURS[activeTour].zodiacDisplay} / ${TENNIS_TOURS[activeTour].element})`}
          </span>
        </div>

        {/* 3-Option DEG3 Switcher + Zero-Lookahead Benchmark Table */}
        <div
          dir="rtl"
          className="mb-5 rounded-xl border-2 border-emerald-300 bg-emerald-50/75 p-2.5 shadow-xs space-y-2.5"
          data-testid="bar-deg3-options"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-1.5">
              {(["opt1", "opt2", "opt3"] as Deg3OptionKey[]).map((ok) => {
                const m = DEG3_OPTIONS[ok];
                const isAct = deg3Opt === ok;
                const isBest = bench?.bestDefaultOption === ok;
                return (
                  <button
                    key={ok}
                    type="button"
                    data-testid={`btn-deg3-${ok}`}
                    onClick={() => switchDeg3(ok)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-extrabold transition-all ${
                      isAct
                        ? "bg-emerald-800 text-white shadow-xs ring-2 ring-amber-400"
                        : "bg-white text-slate-900 hover:bg-emerald-100 border border-emerald-200"
                    }`}
                  >
                    {m.shortFa} {isBest ? "★" : ""}
                  </button>
                );
              })}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {curOptBench && (
                <span className="px-2.5 py-1 rounded bg-white border border-emerald-300 font-mono text-[11px] font-extrabold text-emerald-950" dir="ltr">
                  {`${activeTour} 2024-26 F1: ${curOptBench.total?.f1_wtp?.pct ?? 0}% (${curOptBench.total?.f1_wtp?.rec ?? "0/0"}) • VIP: ${curOptBench.total?.vip?.pct ?? 0}%`}
                </span>
              )}
              <button
                type="button"
                onClick={() => setOpenDeg3Table((v) => !v)}
                className="px-2.5 py-1 rounded-lg bg-white hover:bg-emerald-100 border border-emerald-300 text-emerald-950 text-xs font-extrabold inline-flex items-center gap-1"
              >
                {openDeg3Table ? "بستن جدول مقایسه ۳ آپشن DEG3" : "مقایسه ۳ آپشن DEG3 (۲۰۲۴–۲۰۲۶)"}
                {openDeg3Table ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>

          {openDeg3Table && (
            <div className="bg-white rounded-lg border border-emerald-200 p-2.5 overflow-x-auto space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-extrabold text-slate-800">
                <span>بنچمارک بدون آینده‌نگری ۳ آپشن `DEG3` زاویه اول (`T`) و زاویه دوم (`P`: جنس کورت + کد بازیکن) برای `{activeTour}`:</span>
                <span className="font-mono text-[11px] bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded text-emerald-900" dir="ltr">
                  {curOptMeta.formulaEn}
                </span>
              </div>
              {bench && (
                <table className="w-full text-xs border-collapse font-mono tabular-nums text-right">
                  <thead>
                    <tr className="bg-emerald-50 text-emerald-950 border-b border-emerald-200 font-sans">
                      <th className="py-1.5 px-2">آپشن جمتریا DEG3</th>
                      <th className="py-1.5 px-2">سال ۲۰۲۴</th>
                      <th className="py-1.5 px-2">سال ۲۰۲۵</th>
                      <th className="py-1.5 px-2">سال ۲۰۲۶</th>
                      <th className="py-1.5 px-2">کل ۳ فصل (۲۰۲۴–۲۰۲۶)</th>
                      <th className="py-1.5 px-2">سطح ویژه VIP</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-emerald-100">
                    {(["opt1", "opt2", "opt3"] as Deg3OptionKey[]).map((ok) => {
                      const st = bench.options?.[ok]?.tours?.[activeTour];
                      const isCur = deg3Opt === ok;
                      return (
                        <tr
                          key={ok}
                          onClick={() => switchDeg3(ok)}
                          className={`cursor-pointer ${isCur ? "bg-emerald-50/90 font-bold" : "hover:bg-slate-50"}`}
                        >
                          <td className="py-1.5 px-2 font-sans font-extrabold text-slate-900">
                            {isCur ? "✓ " : ""}{DEG3_OPTIONS[ok].shortFa} {bench.bestDefaultOption === ok ? "★ پیش‌فرض برتر" : ""}
                          </td>
                          <td className="py-1.5 px-2">{st?.["2024"]?.f1_wtp?.pct ?? 0}% ({st?.["2024"]?.f1_wtp?.rec ?? "0/0"})</td>
                          <td className="py-1.5 px-2">{st?.["2025"]?.f1_wtp?.pct ?? 0}% ({st?.["2025"]?.f1_wtp?.rec ?? "0/0"})</td>
                          <td className="py-1.5 px-2">{st?.["2026"]?.f1_wtp?.pct ?? 0}% ({st?.["2026"]?.f1_wtp?.rec ?? "0/0"})</td>
                          <td className="py-1.5 px-2 text-emerald-800 font-extrabold">{st?.total?.f1_wtp?.pct ?? 0}% ({st?.total?.f1_wtp?.rec ?? "0/0"})</td>
                          <td className="py-1.5 px-2 text-indigo-800 font-extrabold">{st?.total?.vip?.pct ?? 0}% ({st?.total?.vip?.rec ?? "0/0"})</td>
                        </tr>
                      );
                    })}
                    {bench.angle_p?.[activeTour] && (
                      <tr className="bg-indigo-50/50 text-indigo-950">
                        <td className="py-1.5 px-2 font-sans font-extrabold">زاویه مکمل P: نام خانوادگی × (Surface + IOC_Code)</td>
                        <td className="py-1.5 px-2">{bench.angle_p[activeTour]["2024"]?.pct ?? 0}% ({bench.angle_p[activeTour]["2024"]?.rec ?? "0/0"})</td>
                        <td className="py-1.5 px-2">{bench.angle_p[activeTour]["2025"]?.pct ?? 0}% ({bench.angle_p[activeTour]["2025"]?.rec ?? "0/0"})</td>
                        <td className="py-1.5 px-2">{bench.angle_p[activeTour]["2026"]?.pct ?? 0}% ({bench.angle_p[activeTour]["2026"]?.rec ?? "0/0"})</td>
                        <td className="py-1.5 px-2 font-extrabold">{bench.angle_p[activeTour].total?.pct ?? 0}% ({bench.angle_p[activeTour].total?.rec ?? "0/0"})</td>
                        <td className="py-1.5 px-2 font-sans text-[11px]">موتور دوم در قفل‌های تلفیقی</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>

        <NbaDashboardTab tour={activeTour} deg3Opt={deg3Opt} />

        <footer className="mt-10 pt-5 border-t border-border/50 text-center">
          <p className="text-xs text-muted-foreground font-mono uppercase tracking-widest">
            TENNIS-SIGNAL-DASHBORD • ATP (DEG1=121 • 1° LEO) &amp; WTA (DEG1=47 • 17° TAURUS) • 3-Option DEG3 Zero-Lookahead Engine
          </p>
        </footer>
      </div>
    </div>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
