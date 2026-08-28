import {
  BarChart3,
  BookOpen,
  Bot,
  Home,
  Map,
  Settings,
  Target,
  UserRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type AppRoute =
  | "/home"
  | "/path"
  | "/skills"
  | "/coach"
  | "/progress"
  | "/resources"
  | "/profile"
  | "/settings";

export type NavigationItem = {
  href: AppRoute;
  label: string;
  icon: LucideIcon;
};

export const primaryNavigation: NavigationItem[] = [
  { href: "/home", label: "Home", icon: Home },
  { href: "/path", label: "My Path", icon: Map },
  { href: "/skills", label: "Skills", icon: Target },
  { href: "/coach", label: "AI Coach", icon: Bot },
  { href: "/progress", label: "Progress", icon: BarChart3 },
];

export const secondaryNavigation: NavigationItem[] = [
  { href: "/resources", label: "Resources", icon: BookOpen },
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/settings", label: "Settings", icon: Settings },
];

export const allNavigation = [...primaryNavigation, ...secondaryNavigation];
