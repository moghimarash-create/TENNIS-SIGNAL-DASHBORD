import { useState } from "react";
import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Activity, ShieldCheck } from "lucide-react";
import NotFound from "@/pages/not-found";
import NbaDashboardTab from "./NbaDashboardTab";
import { TENNIS_TOURS, type TennisTour } from "./tennis-config";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
});

function Home() {
  const [activeTour, setActiveTour] = useState<TennisTour>(() => {
    try {
      const saved = window.localStorage.getItem("tennis_active_tour_tab_v1");
      if (saved === "WTA" || saved === "ATP") return saved;
    } catch {
      // ignore storage restrictions
    }
    return "ATP";
  });

  const switchTour = (tour: TennisTour) => {
    setActiveTour(tour);
    try {
      window.localStorage.setItem("tennis_active_tour_tab_v1", tour);
    } catch {
      // ignore storage restrictions
    }
  };

  const curTour = TENNIS_TOURS[activeTour];

  return (
    <div className="min-h-[100dvh] w-full bg-background flex flex-col font-sans">
      <div className="flex-1 w-full max-w-6xl mx-auto px-4 py-8 md:py-10 flex flex-col">
        <header className="mb-6 flex flex-wrap items-start justify-between gap-4" dir="rtl">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="h-10 w-10 rounded-lg bg-sky-700 text-white flex items-center justify-center shadow-sm">
                <Activity className="h-5 w-5" />
              </div>
              <h1
                className="text-xl md:text-2xl font-extrabold tracking-tight text-slate-900"
                data-testid="text-dashboard-title"
              >
                داشبورد پایه نجومی-جمتریا تنیس (TENNIS-SIGNAL-DASHBORD) • تورنمنت / شهر / زمین مسابقه
              </h1>
            </div>
            <p className="text-slate-600 text-xs md:text-sm max-w-3xl leading-relaxed">
              موتور ۱۰۰٪ نجومی-جمتریا بر پایه نام تورنمنت، شهر و کورت مسابقه + موقعیت سیارات در لحظه و مختصات مسابقه (pyswisseph) + درجه پایه ثابت تور (<b>بدون هیچ وابستگی به تاریخ تولد بازیکنان</b>).
            </p>
          </div>

          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs font-extrabold" dir="rtl">
            <ShieldCheck className="h-4 w-4 text-emerald-700" />
            ایزوله ۱۰۰٪ از شیت‌های NBA و NHL (نوشتن خودکار غیرفعال)
          </div>
        </header>

        {/* Top-Level Tour Switcher (ATP DEG1=121 [1° LEO] vs WTA DEG1=47 [17° TAURUS]) */}
        <div
          dir="rtl"
          className="mb-6 rounded-xl border-2 border-sky-300 bg-sky-50/90 p-2.5 shadow-xs flex flex-wrap items-center justify-between gap-2"
          data-testid="bar-tennis-tours"
        >
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid="tab-tour-atp"
              onClick={() => switchTour("ATP")}
              className={`px-4 py-2 rounded-lg text-xs sm:text-sm font-extrabold transition-all ${
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
              className={`px-4 py-2 rounded-lg text-xs sm:text-sm font-extrabold transition-all ${
                activeTour === "WTA"
                  ? "bg-emerald-700 text-white shadow-sm"
                  : "bg-white text-sky-950 hover:bg-sky-100 border border-sky-200"
              }`}
            >
              تور زنان WTA • جمتریا ۴۰۷ ➔ DEG1 = 47 (17° TAURUS • EARTH • KXWTAMATCH)
            </button>
          </div>
          <span className="px-2.5 py-1 rounded bg-white border border-sky-200 text-[11px] font-mono tabular-nums font-bold text-sky-900" dir="ltr">
            {`${curTour.tour} ACTIVE • GEM=${curTour.gematria} • DEG1=${curTour.deg1} (${curTour.zodiacDisplay} / ${curTour.element}) • ${curTour.kalshiSeries}`}
          </span>
        </div>

        <NbaDashboardTab tour={activeTour} />

        <footer className="mt-10 pt-5 border-t border-border/50 text-center">
          <p className="text-xs text-muted-foreground font-mono uppercase tracking-widest">
            TENNIS-SIGNAL-DASHBORD • ATP (DEG1=121 • 1° LEO • FIRE) &amp; WTA (DEG1=47 • 17° TAURUS • EARTH) • Zero Birthdate Astro-Gematria
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
