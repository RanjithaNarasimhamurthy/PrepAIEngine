"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrainCircuit, BarChart2, MessageSquare, Map, Search } from "lucide-react";
import clsx from "clsx";

const NAV_ITEMS = [
  { href: "/",          label: "Home",      icon: BrainCircuit },
  { href: "/search",    label: "Search",    icon: Search       },
  { href: "/analytics", label: "Analytics", icon: BarChart2    },
  { href: "/assistant", label: "Ask AI",    icon: MessageSquare },
  { href: "/roadmap",   label: "Roadmap",   icon: Map          },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 font-bold text-blue-600 text-lg">
            <BrainCircuit className="w-6 h-6" />
            <span>PrepAI</span>
          </Link>

          {/* Navigation links */}
          <div className="flex items-center gap-1">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  className={clsx(
                    "flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    active
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
