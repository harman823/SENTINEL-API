"use client";

import { useRef } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";

const FaultyTerminal = dynamic(
  () => import("@/components/FaultyTerminal"),
  { ssr: false }
);
import {
  ArrowDown,
  Zap,
  Shield,
  BarChart3,
  FileSearch,
  Code2,
  Send,
  Mail,
  MapPin,
  Phone,
} from "lucide-react";

const NAV_LINKS = [
  { label: "About", href: "#about" },
  { label: "Features", href: "#features" },
  { label: "Contact", href: "#contact" },
];

const FEATURES = [
  {
    icon: FileSearch,
    title: "Spec Analysis",
    desc: "Automatically parse and normalize your OpenAPI specs for comprehensive testing.",
  },
  {
    icon: Zap,
    title: "AI-Powered Tests",
    desc: "LangGraph pipeline generates intelligent, context-aware test cases in seconds.",
  },
  {
    icon: Shield,
    title: "Security Scanning",
    desc: "Detect vulnerabilities, injection risks, and auth bypass issues automatically.",
  },
  {
    icon: BarChart3,
    title: "Risk Scoring",
    desc: "Every endpoint gets a risk score so you can prioritize what matters most.",
  },
  {
    icon: Code2,
    title: "CI/CD Ready",
    desc: "Export results as JSON reports and integrate into your deployment pipeline.",
  },
  {
    icon: Send,
    title: "One-Click Run",
    desc: "Upload your spec, hit analyze, and get a full test report in minutes.",
  },
];

export default function LandingPage() {
  const aboutRef = useRef<HTMLElement>(null);

  return (
    <div className="relative min-h-screen bg-black text-white overflow-x-hidden">
      {/* ─── HERO ─── */}
      <section className="relative h-screen flex flex-col">
        {/* Animated background */}
        <div className="absolute inset-0 z-0">
          <FaultyTerminal
            tint="#00ff88"
            brightness={0.35}
            scale={1.2}
            curvature={0.15}
            scanlineIntensity={0.25}
            glitchAmount={1.2}
            flickerAmount={0.6}
            noiseAmp={0.8}
            mouseReact={true}
            mouseStrength={0.3}
            pageLoadAnimation={true}
            className="w-full h-full"
            style={{}}
          />
          {/* Gradient overlay for readability */}
          <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/30 to-black" />
        </div>

        {/* Navigation */}
        <nav className="relative z-10 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto w-full">
          <span className="text-xl font-bold tracking-tight">
            <span className="text-emerald-400">Auto</span>API
          </span>
          <div className="hidden sm:flex items-center gap-8">
            {NAV_LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="text-sm text-zinc-300 hover:text-emerald-400 transition-colors"
              >
                {l.label}
              </a>
            ))}
            <Link
              href="/drop"
              className="ml-2 inline-flex h-9 items-center rounded-lg bg-emerald-500 px-5 text-sm font-medium text-black hover:bg-emerald-400 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </nav>

        {/* Hero content */}
        <div className="relative z-10 flex-1 flex flex-col items-center justify-center text-center px-6 gap-6 animate-fadeIn">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-xs text-emerald-400 backdrop-blur-sm">
            <Zap className="size-3" />
            AI-Powered API Testing
          </div>
          <h1 className="text-5xl sm:text-7xl font-bold tracking-tight leading-tight max-w-4xl">
            Test Your APIs{" "}
            <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
              Intelligently
            </span>
          </h1>
          <p className="text-lg sm:text-xl text-zinc-400 max-w-2xl leading-relaxed">
            Upload your OpenAPI spec, and let our 12-node AI pipeline generate
            comprehensive tests, find vulnerabilities, and produce actionable
            reports — all in one click.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 mt-4">
            <Link
              href="/drop"
              className="inline-flex h-12 items-center justify-center rounded-xl bg-emerald-500 px-8 text-base font-semibold text-black hover:bg-emerald-400 transition-all hover:scale-105 shadow-lg shadow-emerald-500/25"
            >
              Upload Your Spec →
            </Link>
            <a
              href="#about"
              className="inline-flex h-12 items-center justify-center rounded-xl border border-zinc-700 px-8 text-base font-medium text-zinc-300 hover:border-emerald-500/50 hover:text-white transition-all backdrop-blur-sm"
            >
              Learn More
            </a>
          </div>
        </div>

        {/* Scroll arrow */}
        <div className="relative z-10 flex justify-center pb-10 animate-float">
          <a href="#about" aria-label="Scroll down">
            <ArrowDown className="size-6 text-emerald-400/60" />
          </a>
        </div>
      </section>

      {/* ─── ABOUT ─── */}
      <section
        id="about"
        ref={aboutRef}
        className="relative py-28 px-6 max-w-6xl mx-auto"
      >
        <div className="text-center mb-16 animate-fadeIn">
          <p className="text-emerald-400 text-sm font-semibold tracking-widest uppercase mb-3">
            About us
          </p>
          <h2 className="text-4xl sm:text-5xl font-bold tracking-tight mb-6">
            Why AutoAPI Intelligence?
          </h2>
          <p className="text-zinc-400 max-w-2xl mx-auto text-lg leading-relaxed">
            We built AutoAPI because manually writing API tests is slow,
            error-prone, and never catches everything. Our AI pipeline analyzes
            your entire spec and generates battle-tested scenarios — from happy
            paths to edge-case exploits.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              title: "12-Node Pipeline",
              body: "From spec ingestion to final report, every step is orchestrated by LangGraph for maximum coverage.",
            },
            {
              title: "Zero Config",
              body: "Just drop a YAML or JSON spec. No SDK installs, no test frameworks, no config files needed.",
            },
            {
              title: "Actionable Reports",
              body: "Get pass/fail results, risk scores, and remediation tips — downloadable as JSON or viewed live.",
            },
          ].map((card) => (
            <div
              key={card.title}
              className="group rounded-2xl border border-zinc-800 bg-zinc-900/50 backdrop-blur-md p-8 hover:border-emerald-500/40 transition-all hover:-translate-y-1"
            >
              <h3 className="text-lg font-semibold mb-3 group-hover:text-emerald-400 transition-colors">
                {card.title}
              </h3>
              <p className="text-zinc-400 text-sm leading-relaxed">
                {card.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ─── FEATURES ─── */}
      <section id="features" className="relative py-28 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-emerald-400 text-sm font-semibold tracking-widest uppercase mb-3">
              Features
            </p>
            <h2 className="text-4xl sm:text-5xl font-bold tracking-tight mb-6">
              Everything You Need
            </h2>
            <p className="text-zinc-400 max-w-2xl mx-auto text-lg">
              A complete AI-driven testing toolkit, from parsing to reporting.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="group relative rounded-2xl border border-zinc-800 bg-zinc-900/40 backdrop-blur-md p-8 hover:border-emerald-500/40 transition-all hover:-translate-y-1"
              >
                <div className="mb-4 inline-flex items-center justify-center size-12 rounded-xl bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20 transition-colors">
                  <f.icon className="size-6" />
                </div>
                <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CONTACT ─── */}
      <section id="contact" className="relative py-28 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-emerald-400 text-sm font-semibold tracking-widest uppercase mb-3">
              Contact
            </p>
            <h2 className="text-4xl sm:text-5xl font-bold tracking-tight mb-6">
              Get In Touch
            </h2>
            <p className="text-zinc-400 max-w-xl mx-auto text-lg">
              Have questions or want a demo? Reach out and we&apos;ll get back
              to you within 24 hours.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: Mail,
                label: "Email",
                value: "hello@autoapi.dev",
              },
              {
                icon: Phone,
                label: "Phone",
                value: "+1 (555) 000-1234",
              },
              {
                icon: MapPin,
                label: "Location",
                value: "San Francisco, CA",
              },
            ].map((c) => (
              <div
                key={c.label}
                className="flex flex-col items-center rounded-2xl border border-zinc-800 bg-zinc-900/40 backdrop-blur-md p-8 text-center hover:border-emerald-500/40 transition-all"
              >
                <div className="mb-4 inline-flex items-center justify-center size-12 rounded-xl bg-emerald-500/10 text-emerald-400">
                  <c.icon className="size-5" />
                </div>
                <p className="text-sm text-zinc-500 mb-1">{c.label}</p>
                <p className="font-medium">{c.value}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FOOTER ─── */}
      <footer className="border-t border-zinc-800 py-10 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-zinc-500">
          <span>
            © {new Date().getFullYear()} AutoAPI Intelligence. All rights
            reserved.
          </span>
          <div className="flex gap-6">
            <a href="#about" className="hover:text-zinc-300 transition-colors">
              About
            </a>
            <a
              href="#features"
              className="hover:text-zinc-300 transition-colors"
            >
              Features
            </a>
            <a
              href="#contact"
              className="hover:text-zinc-300 transition-colors"
            >
              Contact
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
