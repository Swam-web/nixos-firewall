#!/usr/bin/env python3
# ==============================================================================
# COSMIC FIREWALL GUI — gestion du pare-feu nftables (config NixOS déclarative)
#
# - Lecture  : ports effectifs via `nix eval` (état déclaratif = état réel)
# - Écriture : JSON de ports (consommé par le module NixOS)
#   . enable      : pare-feu activé/désactivé (mkForce dans le module)
#   . tcp / udp   : ports simples   [{ port, desc, dir }]
#   . tcpRanges / udpRanges : plages [{ from, to, desc, dir }]
#   . dir          : "in" (entrée) / "out" (sortie) / "both" (les deux)
# - Application : nixos-rebuild (validation sans sudo, switch dans un terminal)
#
# Configuration via variables d'environnement (le module NixOS les fixe) :
#   FIREWALL_FLAKE : chemin du flake NixOS    (défaut : auto-détection)
#   FIREWALL_HOST  : hôte du flake            (défaut : nom de la machine)
#   FIREWALL_JSON  : chemin du JSON de ports  (défaut : <flake>/modules/firewall-ports.json)
#
# Interface bilingue : suit la langue du système (LANG), FR sinon EN.
# ==============================================================================
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib
import json
import locale
import os
import shutil
import subprocess
import threading
import time

# ---------------------------------------------------------------- i18n (fr/en)
_lang = ((locale.getlocale()[0] or os.environ.get("LANG") or "en")[:2]).lower()
L = {}

STRINGS = {
    "fr": {
        "title": "Pare-feu NixOS",
        "refresh": "Rafraîchir l'état du pare-feu",
        "fw_label": "Pare-feu",
        "tab_ports": "Ports", "tab_status": "Statut", "tab_journal": "Journal",
        "eff_title": "Configuration effective",
        "readonly": "lecture seule",
        "custom_title": "Ports et plages personnalisés",
        "managed": "gérés par le GUI",
        "add_label": "Ajouter un port ou une plage",
        "add_tip": "Ajouter un port ou une plage personnalisée",
        "hint": "Le pare-feu est déclaratif : modifie les ports, valide le build, puis applique.",
        "validate": "Valider le build",
        "validate_tip": "nixos-rebuild build — vérifie la config, sans sudo",
        "apply": "Appliquer",
        "apply_tip": "Ouvre un terminal avec la commande sudo de switch",
        "copy_tip": "Copier la commande de switch",
        "dlg_add": "Ajouter un port ou une plage", "dlg_edit": "Modifier un port ou une plage",
        "cancel": "Annuler", "ok": "Valider",
        "proto": "Protocole :", "direction": "Direction :", "type": "Type :",
        "dir_in": "Entrée (incoming)", "dir_out": "Sortie (outgoing)", "dir_both": "Les deux",
        "simple_port": "Port simple", "port_range": "Plage de ports",
        "port": "Port :", "frm": "De :", "to": "à :",
        "desc": "Description :",
        "desc_ph": "ex. Serveur Minecraft (facultatif)",
        "range_bad": "Plage invalide — entre des nombres entre 1 et 65535.",
        "range_bad2": "Plage invalide — il faut 1 ≤ de ≤ à ≤ 65535.",
        "port_bad": "Port invalide — entre un nombre entre 1 et 65535.",
        "tcp_range": "TCP (plage)", "udp_range": "UDP (plage)",
        "dir_labels": {"in": "Entrée (incoming)", "out": "Sortie (outgoing)", "both": "Entrée + sortie"},
        "edit_tip": "Modifier", "del_tip": "Supprimer",
        "none_custom": "aucun port ni plage personnalisé",
        "ports_count": "{p} port(s) · {r} plage(s)",
        "journal_title": "Paquets rejetés (6 dernières heures)",
        "journal_empty": "Aucun paquet rejeté journalisé sur les 6 dernières heures.",
        "eval_err": "Erreur d'évaluation nix : {err}",
        "pending": "⚠ Changement d'état du pare-feu en attente — valide puis applique le rebuild.",
        "not_loaded": "état non chargé",
        "saved": "{label} {kind} enregistré — valide puis applique le rebuild.",
        "removed": "{label} {kind} retiré — valide puis applique le rebuild.",
        "build_running": "Build en cours (sans sudo)…",
        "build_ok": "Build OK — configuration valide. Clique sur « Appliquer » pour activer.",
        "build_fail": "Échec du build : {tail}",
        "term_open": "Terminal ouvert — saisis ton mot de passe pour le switch.",
        "term_missing": "Terminal introuvable — commande copiée, colle-la dans un terminal.",
        "dup": "Cette entrée existe déjà dans la liste personnalisée.",
        "disable_title": "Désactiver le pare-feu ?",
        "disable_msg": ("La machine sera exposée au réseau sans filtrage entrant. "
                        "La désactivation ne prendra effet qu'après le rebuild."),
        "fw_on_req": "Pare-feu : activation demandée — valide puis applique le rebuild.",
        "fw_off_req": "⚠ Pare-feu : DÉSACTIVATION demandée — valide puis applique le rebuild.",
        "status": {
            "sys": "Pare-feu (système actuel) :", "gui": "Pare-feu (demandé par le GUI) :",
            "trusted": "Interfaces de confiance :", "log": "Journalisation des refus :",
            "extra": "Règles additionnelles :", "custom": "Ports personnalisés (GUI) :",
            "gen": "Génération courante :", "none": "aucune", "unknown": "inconnue",
            "yes": "oui", "no": "non", "on": "Activé", "off": "Désactivé",
        },
        "status_note": ("Le pare-feu étant déclaratif, l'état affiché correspond exactement "
                        "à la configuration NixOS active."),
        "switch_cmd_fmt": "sudo nixos-rebuild switch --flake {flake}#{host}",
        "ports_count_eff": "{t} TCP · {u} UDP",
        "build_arg": "--apply",
    },
    "en": {
        "title": "NixOS Firewall",
        "refresh": "Refresh firewall state",
        "fw_label": "Firewall",
        "tab_ports": "Ports", "tab_status": "Status", "tab_journal": "Journal",
        "eff_title": "Effective configuration",
        "readonly": "read-only",
        "custom_title": "Custom ports and ranges",
        "managed": "managed by the GUI",
        "add_label": "Add a port or range",
        "add_tip": "Add a custom port or range",
        "hint": "The firewall is declarative: edit ports, validate the build, then apply.",
        "validate": "Validate build",
        "validate_tip": "nixos-rebuild build — checks the config, no sudo needed",
        "apply": "Apply",
        "apply_tip": "Opens a terminal with the sudo switch command",
        "copy_tip": "Copy the switch command",
        "dlg_add": "Add a port or range", "dlg_edit": "Edit port or range",
        "cancel": "Cancel", "ok": "Validate",
        "proto": "Protocol:", "direction": "Direction:", "type": "Type:",
        "dir_in": "Incoming", "dir_out": "Outgoing", "dir_both": "Both",
        "simple_port": "Single port", "port_range": "Port range",
        "port": "Port:", "frm": "From:", "to": "to:",
        "desc": "Description:",
        "desc_ph": "e.g. Minecraft server (optional)",
        "range_bad": "Invalid range — enter numbers between 1 and 65535.",
        "range_bad2": "Invalid range — 1 ≤ from ≤ to ≤ 65535 required.",
        "port_bad": "Invalid port — enter a number between 1 and 65535.",
        "tcp_range": "TCP (range)", "udp_range": "UDP (range)",
        "dir_labels": {"in": "Incoming", "out": "Outgoing", "both": "Incoming + outgoing"},
        "edit_tip": "Edit", "del_tip": "Delete",
        "none_custom": "no custom port or range",
        "ports_count": "{p} port(s) · {r} range(s)",
        "journal_title": "Rejected packets (last 6 hours)",
        "journal_empty": "No rejected packet logged in the last 6 hours.",
        "eval_err": "Nix evaluation error: {err}",
        "pending": "⚠ Firewall state change pending — validate then apply the rebuild.",
        "not_loaded": "state not loaded",
        "saved": "{label} {kind} saved — validate then apply the rebuild.",
        "removed": "{label} {kind} removed — validate then apply the rebuild.",
        "build_running": "Building (no sudo)…",
        "build_ok": "Build OK — valid configuration. Click “Apply” to activate.",
        "build_fail": "Build failed: {tail}",
        "term_open": "Terminal opened — enter your password to switch.",
        "term_missing": "No terminal found — command copied, paste it in a terminal.",
        "dup": "This entry already exists in the custom list.",
        "disable_title": "Disable the firewall?",
        "disable_msg": ("The machine will be exposed to the network without incoming filtering. "
                        "The change takes effect only after the rebuild."),
        "fw_on_req": "Firewall: enabling requested — validate then apply the rebuild.",
        "fw_off_req": "⚠ Firewall: DISABLING requested — validate then apply the rebuild.",
        "status": {
            "sys": "Firewall (current system):", "gui": "Firewall (requested by GUI):",
            "trusted": "Trusted interfaces:", "log": "Log refused connections:",
            "extra": "Extra rules:", "custom": "Custom ports (GUI):",
            "gen": "Current generation:", "none": "none", "unknown": "unknown",
            "yes": "yes", "no": "no", "on": "Enabled", "off": "Disabled",
        },
        "status_note": ("The firewall being declarative, the displayed state exactly matches "
                        "the active NixOS configuration."),
        "switch_cmd_fmt": "sudo nixos-rebuild switch --flake {flake}#{host}",
        "ports_count_eff": "{t} TCP · {u} UDP",
        "build_arg": "--apply",
    },
}
L = STRINGS.get(_lang, STRINGS["en"])

def tr(key, **kw):
    v = L.get(key, STRINGS["en"].get(key, key))
    return v.format(**kw) if kw else v

# ------------------------------------------------------- flake / host / json
def _detect_flake():
    env = os.environ.get("FIREWALL_FLAKE")
    if env:
        return env
    # flake à la racine du disque de config classique
    for cand in ("/persist/nixos", "/etc/nixos", "~/nixos"):
        p = os.path.expanduser(cand)
        if os.path.isfile(os.path.join(p, "flake.nix")):
            return p
    return "/etc/nixos"

FLAKE = _detect_flake()
HOST = os.environ.get("FIREWALL_HOST", os.uname().nodename)
JSON_PATH = os.environ.get(
    "FIREWALL_JSON", os.path.join(FLAKE, "modules", "firewall-ports.json"))
SWITCH_CMD = tr("switch_cmd_fmt", flake=FLAKE, host=HOST)
BUILD_CMD = ["nixos-rebuild", "build", "--flake", f"{FLAKE}#{HOST}"]

PORT_LABELS = {
    49222: "SSH", 631: "CUPS / IPP", 80: "HTTP", 443: "HTTPS",
    9100: "JetDirect printing", 161: "SNMP", 162: "SNMP-Trap",
    5353: "Avahi mDNS", 427: "SLP", 27015: "Steam", 27036: "Steam",
    3478: "Discord / PSN voice", 3479: "Discord / PSN voice",
    3480: "Discord / PSN voice", 4380: "Steam",
}

EVAL_APPLY = (
    "f: { enable = f.enable; tcp = f.allowedTCPPorts; udp = f.allowedUDPPorts; "
    "tcpRanges = f.allowedTCPPortRanges; udpRanges = f.allowedUDPPortRanges; "
    "trusted = f.trustedInterfaces; logRefused = f.logRefusedConnections; "
    "extraRules = f.extraInputRules; }"
)

KIND_LABELS = {
    "tcp": "TCP", "udp": "UDP",
    "tcpRanges": tr("tcp_range"), "udpRanges": tr("udp_range"),
}

# Direction : badge lisible + infobulle
DIR_BADGES = {
    "in":   {"badge": "↓", "label": tr("dir_labels")["in"]},
    "out":  {"badge": "↑", "label": tr("dir_labels")["out"]},
    "both": {"badge": "⇅", "label": tr("dir_labels")["both"]},
}

# Terminal pour le sudo : $TERMINAL puis détection par ordre usuel.
# Retourne (prg, pré-args, post-args) — la commande est insérée entre les deux.
TERMINALS = [
    ("xdg-terminal-exec", []), ("cosmic-term", ["--exec"]),
    ("ptyxis", ["--"]), ("gnome-terminal", ["--"]),
    ("konsole", ["-e"]), ("kitty", ["--hold", "bash", "-c"]),
    ("foot", ["-e", "bash", "-c"]), ("alacritty", ["-e", "bash", "-c"]),
    ("wezterm", ["exec", "--"]), ("xfce4-terminal", ["-e", "bash", "-c"]),
]

def find_terminal():
    """(prg, argv_base) pour lancer `bash -c CMD` dans un terminal, ou None."""
    t = os.environ.get("TERMINAL")
    if t and shutil.which(t):
        return (t, [])
    for prg, args in TERMINALS:
        if shutil.which(prg):
            return (prg, list(args))
    return None

def launch_switch_terminal(cmd):
    """Ouvre un terminal exécutant `cmd` (hold si supporté). True si lancé."""
    term = find_terminal()
    if term is None:
        return False
    prg, base = term
    # kitty/foot/alacritty/xfce4-terminal : base finit par bash -c → cmd direct
    if base and base[-2:] == ["bash", "-c"]:
        argv = [prg] + base + [cmd]
    else:
        argv = [prg] + base + ["sudo", "nixos-rebuild", "switch",
                               "--flake", f"{FLAKE}#{HOST}"]
    subprocess.Popen(argv, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def run(cmd, timeout=180):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def load_custom():
    try:
        with open(JSON_PATH) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault("enable", True)
    for k in ("tcp", "udp", "tcpRanges", "udpRanges"):
        data.setdefault(k, [])
    return data


def save_custom(data):
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


class PortDialog(Gtk.Dialog):
    """Dialogue add/edit : port simple ou plage, TCP/UDP, description."""

    def __init__(self, parent, kind="tcp", entry=None):
        title = tr("dlg_edit") if entry else tr("dlg_add")
        super().__init__(title=title,
                         transient_for=parent, modal=True)
        self.add_button(tr("cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(tr("ok"), Gtk.ResponseType.OK)
        self.result = None

        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(14)
        box.set_margin_end(14)

        grid = Gtk.Grid(row_spacing=10, column_spacing=12)

        grid.attach(Gtk.Label(label=tr("proto"), halign=Gtk.Align.END), 0, 0, 1, 1)
        self.proto_combo = Gtk.ComboBoxText()
        self.proto_combo.append_text("TCP")
        self.proto_combo.append_text("UDP")
        self.proto_combo.set_active(0 if "tcp" in kind else 1)
        grid.attach(self.proto_combo, 1, 0, 1, 1)

        # --- direction (entrant / sortant / les deux)
        grid.attach(Gtk.Label(label=tr("direction"), halign=Gtk.Align.END), 0, 1, 1, 1)
        self.dir_combo = Gtk.ComboBoxText()
        self.dir_combo.append_text(tr("dir_in"))
        self.dir_combo.append_text(tr("dir_out"))
        self.dir_combo.append_text(tr("dir_both"))
        cur_dir = (entry or {}).get("dir", "in")
        self.dir_combo.set_active({"in": 0, "out": 1, "both": 2}.get(cur_dir, 0))
        grid.attach(self.dir_combo, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label=tr("type"), halign=Gtk.Align.END), 0, 2, 1, 1)
        self.type_combo = Gtk.ComboBoxText()
        self.type_combo.append_text(tr("simple_port"))
        self.type_combo.append_text(tr("port_range"))
        self.type_combo.set_active(1 if "Ranges" in kind else 0)
        self.type_combo.connect("changed", self._on_type_changed)
        grid.attach(self.type_combo, 1, 2, 1, 1)

        # --- port simple
        self.simple_box = Gtk.Box(spacing=8)
        self.simple_box.append(Gtk.Label(label=tr("port"), halign=Gtk.Align.END))
        self.port_entry = Gtk.Entry(input_purpose=Gtk.InputPurpose.NUMBER,
                                    max_length=5, placeholder_text="ex. 25565")
        self.simple_box.append(self.port_entry)
        grid.attach(self.simple_box, 0, 3, 2, 1)

        # --- plage
        self.range_box = Gtk.Box(spacing=8)
        self.range_box.append(Gtk.Label(label=tr("frm"), halign=Gtk.Align.END))
        self.from_entry = Gtk.Entry(input_purpose=Gtk.InputPurpose.NUMBER,
                                    max_length=5, placeholder_text="ex. 27000")
        self.range_box.append(self.from_entry)
        self.range_box.append(Gtk.Label(label=tr("to"), halign=Gtk.Align.END))
        self.to_entry = Gtk.Entry(input_purpose=Gtk.InputPurpose.NUMBER,
                                  max_length=5, placeholder_text="ex. 27030")
        self.range_box.append(self.to_entry)
        grid.attach(self.range_box, 0, 4, 2, 1)

        grid.attach(Gtk.Label(label=tr("desc"), halign=Gtk.Align.END), 0, 5, 1, 1)
        self.desc_entry = Gtk.Entry(placeholder_text=tr("desc_ph"))
        grid.attach(self.desc_entry, 1, 5, 1, 1)

        box.append(grid)
        self.set_default_response(Gtk.ResponseType.OK)

        if entry:
            if "Ranges" in kind:
                self.from_entry.set_text(str(entry["from"]))
                self.to_entry.set_text(str(entry["to"]))
            else:
                self.port_entry.set_text(str(entry["port"]))
            self.desc_entry.set_text(entry.get("desc", ""))

        self._on_type_changed()

    def _on_type_changed(self, *args):
        is_range = self.type_combo.get_active() == 1
        self.simple_box.set_visible(not is_range)
        self.range_box.set_visible(is_range)

    def validate(self):
        is_range = self.type_combo.get_active() == 1
        proto = self.proto_combo.get_active_text().lower()
        desc = self.desc_entry.get_text().strip()
        kind = proto + ("Ranges" if is_range else "")
        dir_ = ("in", "out", "both")[self.dir_combo.get_active()]

        def bad(msg):
            err = Gtk.MessageDialog(transient_for=self, modal=True,
                                    message_type=Gtk.MessageType.ERROR,
                                    buttons=Gtk.ButtonsType.CLOSE, text=msg)
            err.connect("response", lambda d, r: d.destroy())
            err.present()

        if is_range:
            f, t = self.from_entry.get_text().strip(), self.to_entry.get_text().strip()
            if not (f.isdigit() and t.isdigit()):
                bad(tr("range_bad"))
                return None
            f, t = int(f), int(t)
            if not (1 <= f <= t <= 65535):
                bad(tr("range_bad2"))
                return None
            return {"kind": kind, "entry": {"from": f, "to": t, "desc": desc, "dir": dir_}}

        raw = self.port_entry.get_text().strip()
        if not (raw.isdigit() and 1 <= int(raw) <= 65535):
            bad(tr("port_bad"))
            return None
        return {"kind": kind, "entry": {"port": int(raw), "desc": desc, "dir": dir_}}


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title(tr("title"))
        self.set_default_size(880, 660)

        self.eff = {}
        self.custom = load_custom()
        self._switch_busy = False

        provider = Gtk.CssProvider()
        provider.load_from_data("textview.mono { font-family: monospace; }".encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        # Bouton rafraîchir
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text(tr("refresh"))
        refresh_btn.connect("clicked", self.on_refresh)
        header.pack_start(refresh_btn)

        # Interrupteur activer/désactiver (état demandé, appliqué au rebuild)
        fw_box = Gtk.Box(spacing=6)
        fw_lbl = Gtk.Label(label=f"<b>{tr('fw_label')}</b>")
        fw_lbl.set_use_markup(True)
        fw_box.append(fw_lbl)
        self.fw_switch = Gtk.Switch()
        self.fw_switch.set_valign(Gtk.Align.CENTER)
        self.fw_switch.connect("notify::active", self.on_toggle_fw)
        fw_box.append(self.fw_switch)
        header.pack_end(fw_box)

        self.head_spin = Gtk.Spinner()
        header.pack_end(self.head_spin)

        switcher = Gtk.StackSwitcher()
        header.set_title_widget(switcher)

        self.stack = Gtk.Stack()
        switcher.set_stack(self.stack)
        self.set_child(self.stack)
        self.stack.add_titled(self._build_ports_page(), "ports", tr("tab_ports"))
        self.stack.add_titled(self._build_status_page(), "statut", tr("tab_status"))
        self.stack.add_titled(self._build_journal_page(), "journal", tr("tab_journal"))

        self._sync_fw_switch()
        self._load_journal()
        self.on_refresh()

    # ------------------------------------------------------------------ pages
    def _build_ports_page(self):
        # Structure : tout est FIXE sauf le contenu des listes.
        #   [Frame effective]  titre + compteur FIXES, liste scrollable
        #   [Frame personnalisé] titre FIXE, liste scrollable
        #   [Barre d'action]    Ajouter / message / Valider / Appliquer FIXES
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        def margins(w, top=12, bottom=0, start=12, end=12):
            w.set_margin_top(top)
            w.set_margin_bottom(bottom)
            w.set_margin_start(start)
            w.set_margin_end(end)
            return w

        # ---------------------------------------------------------------- fixed
        frame_eff = Gtk.Frame()
        eff_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        # header fixe : titre + compteur de ports
        eff_header = Gtk.Box(spacing=8)
        eff_header = margins(eff_header, 8, 6, 10, 10)
        eff_title = Gtk.Label(label=f"<b>{tr('eff_title')}</b> <span size='smaller' weight='bold'>({tr('readonly')})</span>")
        eff_title.set_use_markup(True)
        eff_title.set_halign(Gtk.Align.START)
        eff_header.append(eff_title)
        self.eff_count_lbl = Gtk.Label(label="…")
        self.eff_count_lbl.add_css_class("dim-label")
        self.eff_count_lbl.set_halign(Gtk.Align.END)
        self.eff_count_lbl.set_hexpand(True)
        eff_header.append(self.eff_count_lbl)
        eff_outer.append(eff_header)
        # liste scrollable
        self.eff_box = Gtk.ListBox()
        self.eff_box.set_selection_mode(Gtk.SelectionMode.NONE)
        eff_scroll = Gtk.ScrolledWindow()
        eff_scroll.set_vexpand(True)
        eff_scroll.set_min_content_height(160)
        eff_scroll.set_child(self.eff_box)
        eff_outer.append(eff_scroll)
        frame_eff.set_child(eff_outer)
        box.append(margins(frame_eff, 12, 0))

        # ---------------------------------------------------------------- custom
        frame_custom = Gtk.Frame()
        cust_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        cust_header = Gtk.Box(spacing=8)
        cust_header = margins(cust_header, 8, 6, 10, 10)
        cust_title = Gtk.Label(label=f"<b>{tr('custom_title')}</b> <span size='smaller' weight='bold'>({tr('managed')})</span>")
        cust_title.set_use_markup(True)
        cust_title.set_halign(Gtk.Align.START)
        cust_header.append(cust_title)
        self.custom_count_lbl = Gtk.Label(label="")
        self.custom_count_lbl.add_css_class("dim-label")
        self.custom_count_lbl.set_halign(Gtk.Align.END)
        self.custom_count_lbl.set_hexpand(True)
        cust_header.append(self.custom_count_lbl)
        cust_outer.append(cust_header)
        # liste scrollable
        self.custom_box = Gtk.ListBox()
        self.custom_box.set_selection_mode(Gtk.SelectionMode.NONE)
        cust_scroll = Gtk.ScrolledWindow()
        cust_scroll.set_vexpand(True)
        cust_scroll.set_min_content_height(120)
        cust_scroll.set_child(self.custom_box)
        cust_outer.append(cust_scroll)
        frame_custom.set_child(cust_outer)
        box.append(margins(frame_custom, 0, 0))

        # Barre d'action FIXE (hors scroll) : le bouton Ajouter ne doit pas
        # défiler avec la liste — il reste ancré à côté de Valider/Appliquer.
        bar = Gtk.Box(spacing=8)
        bar.set_margin_start(12)
        bar.set_margin_end(12)
        bar.set_margin_top(6)
        bar.set_margin_bottom(12)

        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.set_label(tr("add_label"))
        add_btn.set_tooltip_text(tr("add_tip"))
        add_btn.connect("clicked", self.on_add)
        bar.append(add_btn)
        self.build_lbl = Gtk.Label(label=tr("hint"))
        self.build_lbl.set_hexpand(True)
        self.build_lbl.set_xalign(0)
        self.build_lbl.set_wrap(True)
        self.build_lbl.add_css_class("dim-label")
        bar.append(self.build_lbl)

        self.build_spin = Gtk.Spinner()
        bar.append(self.build_spin)

        val_btn = Gtk.Button(label=tr("validate"))
        val_btn.set_tooltip_text(tr("validate_tip"))
        val_btn.connect("clicked", self.on_validate_build)
        bar.append(val_btn)

        apply_btn = Gtk.Button(label=tr("apply"))
        apply_btn.set_tooltip_text(tr("apply_tip"))
        apply_btn.add_css_class("suggested-action")
        apply_btn.connect("clicked", self.on_apply)
        bar.append(apply_btn)

        copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
        copy_btn.set_tooltip_text(tr("copy_tip"))
        copy_btn.connect("clicked", self.on_copy)
        bar.append(copy_btn)

        box.append(bar)
        return box

    def _build_status_page(self):
        scroll = Gtk.ScrolledWindow()
        grid = Gtk.Grid(row_spacing=10, column_spacing=14)
        grid.set_margin_top(14)
        grid.set_margin_bottom(14)
        grid.set_margin_start(14)
        grid.set_margin_end(14)
        scroll.set_child(grid)
        self.status_grid = grid
        return scroll

    def _build_journal_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(12)
        box.set_margin_end(12)

        toolbar = Gtk.Box(spacing=8)
        lbl = Gtk.Label(label=f"<b>{tr('journal_title')}</b>")
        lbl.set_use_markup(True)
        lbl.set_hexpand(True)
        lbl.set_xalign(0)
        toolbar.append(lbl)
        self.jr_spin = Gtk.Spinner()
        toolbar.append(self.jr_spin)
        jr_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        jr_btn.connect("clicked", self.on_journal_refresh)
        toolbar.append(jr_btn)
        box.append(toolbar)

        self.jr_view = Gtk.TextView()
        self.jr_view.set_editable(False)
        self.jr_view.set_cursor_visible(False)
        self.jr_view.set_css_classes(["mono"])
        self.jr_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(self.jr_view)
        box.append(scroll)
        return box

    # --------------------------------------------------------------- refresh
    def on_refresh(self, *args):
        self.head_spin.start()
        threading.Thread(target=self._eval_thread, daemon=True).start()

    def on_journal_refresh(self, *args):
        self._load_journal()

    def _load_journal(self):
        self.jr_spin.start()
        threading.Thread(target=self._journal_thread, daemon=True).start()

    def _journal_thread(self):
        rc, out, err = run(
            ["journalctl", "-k", "--since", "6 hours ago", "--no-pager"],
            timeout=120,
        )
        lines = [ln for ln in out.splitlines()
                 if "nixos-fw" in ln or "FINAL_REJECT" in ln]
        GLib.idle_add(self._journal_done, "\n".join(lines[-200:]))

    def _journal_done(self, text):
        self.jr_spin.stop()
        buf = self.jr_view.get_buffer()
        buf.set_text(text if text.strip() else tr("journal_empty"))
        return False

    def _eval_thread(self):
        rc, out, err = run(
            ["nix", "eval", "--json",
             f"{FLAKE}#nixosConfigurations.{HOST}.config.networking.firewall",
             "--apply", EVAL_APPLY],
            timeout=240,
        )
        if rc != 0:
            GLib.idle_add(self._eval_done, None, err[-600:])
        else:
            try:
                GLib.idle_add(self._eval_done, json.loads(out), None)
            except json.JSONDecodeError as e:
                GLib.idle_add(self._eval_done, None, str(e))

    def _eval_done(self, data, err):
        self.head_spin.stop()
        if err is not None:
            self.build_lbl.set_text(tr("eval_err", err=err))
            return False
        self.eff = data
        self.render_effective()
        self.render_status()
        # Rappel si l'état demandé diffère de l'état système
        if self.eff.get("enable", True) != self.custom.get("enable", True):
            self.build_lbl.set_text(tr("pending"))
        return False

    # ------------------------------------------------------------- rendering
    def _clear_listbox(self, lb):
        child = lb.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            lb.remove(child)
            child = nxt

    def _port_row(self, port_txt, proto, desc):
        row = Gtk.ListBoxRow()
        row_box = Gtk.Box(spacing=10)
        row_box.set_margin_top(7)
        row_box.set_margin_bottom(7)
        row_box.set_margin_start(10)
        row_box.set_margin_end(10)

        lbl = Gtk.Label()
        lbl.set_markup(f"<b>{port_txt}</b>  <span size='smaller' weight='bold'>{proto}</span>"
                       + (f" — <span size='smaller'>{desc}</span>" if desc else ""))
        lbl.set_hexpand(True)
        lbl.set_xalign(0)
        row_box.append(lbl)
        row.set_child(row_box)
        return row, row_box

    def render_effective(self):
        self._clear_listbox(self.eff_box)
        if not self.eff:
            row, _ = self._port_row("…", "", tr("not_loaded"))
            self.eff_box.append(row)
            self.eff_count_lbl.set_text("…")
            return
        tcp = sorted(self.eff.get("tcp", []))
        udp = sorted(self.eff.get("udp", []))
        for p in tcp:
            row, _ = self._port_row(str(p), "TCP", PORT_LABELS.get(p, ""))
            self.eff_box.append(row)
        for p in udp:
            row, _ = self._port_row(str(p), "UDP", PORT_LABELS.get(p, ""))
            self.eff_box.append(row)
        for r in self.eff.get("tcpRanges", []):
            row, _ = self._port_row(f"{r['from']}–{r['to']}", "TCP", tr("port_range"))
            self.eff_box.append(row)
        for r in self.eff.get("udpRanges", []):
            row, _ = self._port_row(f"{r['from']}–{r['to']}", "UDP", tr("port_range"))
            self.eff_box.append(row)
        # compteur FIXE dans le header (ne défile pas avec la liste)
        self.eff_count_lbl.set_text(f"{len(tcp)} TCP · {len(udp)} UDP")

    def render_custom(self):
        self._clear_listbox(self.custom_box)
        n = 0

        def entry_text(e, is_range):
            return f"{e['from']}–{e['to']}" if is_range else str(e["port"])

        for kind in ("tcp", "udp", "tcpRanges", "udpRanges"):
            is_range = "Ranges" in kind
            entries = self.custom.get(kind, [])
            key = (lambda e: (e.get("from", 0), e.get("to", 0))) if is_range \
                else (lambda e: e.get("port", 0))
            for entry in sorted(entries, key=key):
                d = entry.get("dir", "in")
                row, row_box = self._port_row(
                    entry_text(entry, is_range), KIND_LABELS[kind],
                    entry.get("desc", ""))
                # badge direction entre le texte et les boutons
                dir_lbl = Gtk.Label(label=DIR_BADGES[d]["badge"])
                dir_lbl.set_tooltip_text(DIR_BADGES[d]["label"])
                dir_lbl.set_valign(Gtk.Align.CENTER)
                row_box.append(dir_lbl)
                edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
                edit_btn.set_valign(Gtk.Align.CENTER)
                edit_btn.set_tooltip_text(tr("edit_tip"))
                edit_btn.connect("clicked", self.on_edit, kind, entry)
                row_box.append(edit_btn)

                del_btn = Gtk.Button(icon_name="edit-delete-symbolic")
                del_btn.set_valign(Gtk.Align.CENTER)
                del_btn.set_tooltip_text(tr("del_tip"))
                del_btn.connect("clicked", self.on_delete, kind, entry)
                row_box.append(del_btn)
                self.custom_box.append(row)
                n += 1

        if n == 0:
            row, _ = self._port_row("—", "", tr("none_custom"))
            self.custom_box.append(row)
        # compteur FIXE dans le header (ne défile pas avec la liste)
        n_ports = len(self.custom.get("tcp", [])) + len(self.custom.get("udp", []))
        n_ranges = len(self.custom.get("tcpRanges", [])) + len(self.custom.get("udpRanges", []))
        self.custom_count_lbl.set_text(tr("ports_count", p=n_ports, r=n_ranges))

    def render_status(self):
        grid = self.status_grid
        child = grid.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            grid.remove(child)
            child = nxt

        def add_row(title, value, idx):
            t = Gtk.Label(label=f"<b>{title}</b>")
            t.set_use_markup(True)
            t.set_halign(Gtk.Align.END)
            v = Gtk.Label(label=value)
            v.set_halign(Gtk.Align.START)
            v.set_selectable(True)
            grid.attach(t, 0, idx, 1, 1)
            grid.attach(v, 1, idx, 1, 1)

        eff_on = self.eff.get("enable", True)
        S = L["status"]
        add_row(S["sys"], S["on"] if eff_on else S["off"], 0)
        add_row(S["gui"], S["on"] if self.custom.get("enable", True) else S["off"], 1)
        add_row(S["trusted"], ", ".join(self.eff.get("trusted", [])) or S["none"], 2)
        add_row(S["log"], S["yes"] if self.eff.get("logRefused") else S["no"], 3)

        rules = self.eff.get("extraRules", "")
        rule_lines = [ln.strip() for ln in rules.splitlines()
                      if ln.strip() and "accept" in ln]
        add_row(S["extra"], rule_lines[0] if rule_lines else S["none"], 4)

        n_ports = len(self.custom.get("tcp", [])) + len(self.custom.get("udp", []))
        n_ranges = len(self.custom.get("tcpRanges", [])) + len(self.custom.get("udpRanges", []))
        add_row(S["custom"], tr("ports_count", p=n_ports, r=n_ranges), 5)

        try:
            gen = os.path.basename(os.path.realpath("/run/current-system"))
            mtime = time.ctime(os.stat("/run/current-system").st_mtime)
            add_row(S["gen"], f"{gen[:40]}… ({mtime})", 6)
        except OSError:
            add_row(S["gen"], S["unknown"], 6)

        note = Gtk.Label(label=tr("status_note"))
        note.set_wrap(True)
        note.add_css_class("dim-label")
        grid.attach(note, 0, 8, 2, 1)

    # -------------------------------------------------------- toggle firewall
    def _sync_fw_switch(self):
        self._switch_busy = True
        self.fw_switch.set_active(bool(self.custom.get("enable", True)))
        self._switch_busy = False

    def on_toggle_fw(self, switch, param):
        if self._switch_busy:
            return
        desired = switch.get_active()

        if not desired:
            confirm = Gtk.MessageDialog(
                transient_for=self, modal=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text=tr("disable_title"),
                secondary_text=tr("disable_msg"),
            )
            confirm.connect("response", self._on_disable_confirmed)
            confirm.present()
        else:
            self.custom["enable"] = True
            save_custom(self.custom)
            self.build_lbl.set_text(tr("fw_on_req"))

    def _on_disable_confirmed(self, dlg, response):
        if response == Gtk.ResponseType.OK:
            self.custom["enable"] = False
            save_custom(self.custom)
            self.build_lbl.set_text(tr("fw_off_req"))
            self.render_status()
        else:
            self._sync_fw_switch()
        dlg.destroy()

    # ------------------------------------------------------------- add/edit
    def on_add(self, *args):
        dlg = PortDialog(self)
        dlg.connect("response", self._port_dialog_response, None, None)
        dlg.present()

    def on_edit(self, btn, kind, entry):
        dlg = PortDialog(self, kind=kind, entry=entry)
        dlg.connect("response", self._port_dialog_response, kind, entry)
        dlg.present()

    def _port_dialog_response(self, dlg, response, kind, entry):
        if response == Gtk.ResponseType.OK:
            res = dlg.validate()
            if res is not None:
                new_kind, new_entry = res["kind"], res["entry"]
                # unicité (hors édition de soi-même)
                for k in ("tcp", "udp", "tcpRanges", "udpRanges"):
                    for other in self.custom.get(k, []):
                        if other is entry:
                            continue
                        same = (new_entry.get("port") == other.get("port") and
                                "Ranges" not in new_kind and "Ranges" not in k) or \
                               (new_entry.get("from") == other.get("from") and
                                new_entry.get("to") == other.get("to") and
                                "Ranges" in new_kind and "Ranges" in k)
                        if same:
                            err = Gtk.MessageDialog(
                                transient_for=self, modal=True,
                                message_type=Gtk.MessageType.WARNING,
                                buttons=Gtk.ButtonsType.CLOSE,
                                text=tr("dup"),
                            )
                            err.connect("response", lambda d, r: d.destroy())
                            err.present()
                            return
                # édition : retirer l'ancienne entrée de son genre précédent
                if entry is not None and kind is not None:
                    lst = self.custom.get(kind, [])
                    if entry in lst:
                        lst.remove(entry)
                self.custom.setdefault(new_kind, []).append(new_entry)
                save_custom(self.custom)
                self.render_custom()
                self.render_status()
                label = (f"{new_entry.get('from')}–{new_entry.get('to')}"
                         if "Ranges" in new_kind else str(new_entry.get("port")))
                self.build_lbl.set_text(
                    tr("saved", label=label, kind=KIND_LABELS[new_kind]))
        dlg.destroy()

    def on_delete(self, btn, kind, entry):
        lst = self.custom.get(kind, [])
        if entry in lst:
            lst.remove(entry)
        save_custom(self.custom)
        self.render_custom()
        self.render_status()
        label = (f"{entry.get('from')}–{entry.get('to')}" if "Ranges" in kind
                 else str(entry.get("port")))
        self.build_lbl.set_text(
            tr("removed", label=label, kind=KIND_LABELS[kind]))

    # ----------------------------------------------------------------- build
    def on_validate_build(self, *args):
        self.build_spin.start()
        self.build_lbl.set_text(tr("build_running"))
        threading.Thread(target=self._build_thread, daemon=True).start()

    def _build_thread(self):
        rc, out, err = run(BUILD_CMD, timeout=1800)
        tail = " | ".join((err or out).splitlines()[-4:]) if (err or out) else ""
        GLib.idle_add(self._build_done, rc, tail)

    def _build_done(self, rc, tail):
        self.build_spin.stop()
        if rc == 0:
            self.build_lbl.set_text(tr("build_ok"))
        else:
            self.build_lbl.set_text(tr("build_fail", tail=tail))
        return False

    def on_apply(self, *args):
        if launch_switch_terminal(SWITCH_CMD):
            self.build_lbl.set_text(tr("term_open"))
        else:
            self.on_copy()
            self.build_lbl.set_text(tr("term_missing"))

    def on_copy(self, *args):
        clip = Gdk.Display.get_default().get_clipboard()
        clip.set_text(SWITCH_CMD)


class FirewallApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.mynixos.firewall-gui")
        self.win = None

    def do_activate(self):
        if self.win is None:
            self.win = MainWindow(self)
        self.win.present()


if __name__ == "__main__":
    import sys
    app = FirewallApp()
    sys.exit(app.run(sys.argv))
