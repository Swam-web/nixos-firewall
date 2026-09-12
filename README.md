# NixOS Firewall

**GTK4 manager + COSMIC applet** for the [NixOS](https://nixos.org) declarative firewall.

- **GUI** (`firewall-gui`): manage ports/ranges (TCP/UDP, incoming/outgoing/both), enable/disable the firewall, view effective configuration, status and rejected-packet journal. GTK4 — works on COSMIC, GNOME, KDE Plasma, XFCE, sway...
- **Applet** (`cosmic-applet-firewall`): COSMIC panel applet, shield icon — green = active, red = disabled. Click opens the GUI.
- **Declarative**: the GUI writes `firewall-ports.json`, the NixOS module imports it. Apply with `nixos-rebuild` (validated build, then sudo switch from a terminal).

![screenshot placeholder](https://github.com/Swam-web/nixos-firewall/raw/main/docs/screenshot.png)

## Install

### Flake

```nix
# flake.nix
{
  inputs.nixos-firewall.url = "github:Swam-web/nixos-firewall";
}
```

```nix
# configuration.nix
{ inputs, ... }: {
  imports = [ inputs.nixos-firewall.nixosModules.default ];

  programs.nixos-firewall = {
    enable = true;
    flake = "/persist/nixos";   # your flake path
    host = "intel";             # nixosConfigurations.<host>
    applet.enable = true;       # COSMIC panel applet
  };
}
```

Then:

```sh
nixos-rebuild switch --flake /persist/nixos#intel
```

### Try without installing

```sh
nix run github:Swam-web/nixos-firewall#firewall-gui
```

## How it works

1. **Add a port/range** in the GUI (protocol, direction incoming/outgoing/both, description).
2. The entry is saved in `<flake>/modules/firewall-ports.json`.
3. **Validate build** (no sudo) — `nixos-rebuild build` checks the configuration.
4. **Apply** — opens a terminal with `sudo nixos-rebuild switch`.
5. The NixOS module imports the JSON: `dir: "in"` entries feed `networking.firewall` (native), `out`/`both` entries go to a dedicated nftables output table.

The firewall stays **declarative**: the GUI never touches runtime state, it edits the source of truth and rebuilds.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `programs.nixos-firewall.enable` | `false` | Enable the module |
| `programs.nixos-firewall.flake` | — | Path of your NixOS flake |
| `programs.nixos-firewall.host` | — | Flake host (`nixosConfigurations.<host>`) |
| `programs.nixos-firewall.firewallJsonFile` | `<flake>/modules/firewall-ports.json` | Custom JSON path |
| `programs.nixos-firewall.applet.enable` | `true` | COSMIC panel applet |

## i18n

The GUI follows the system language automatically: **français / English** (more languages welcome — add a dict in `gui/app.py`).

## Packages

```sh
nix build github:Swam-web/nixos-firewall#firewall-gui
nix build github:Swam-web/nixos-firewall#cosmic-applet-firewall
```

## License

GPL-3.0-only
