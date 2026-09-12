# NixOS Firewall

**GTK4 manager + COSMIC applet** for the [NixOS](https://nixos.org) declarative firewall.

- **GUI** (`firewall-gui`): manage ports/ranges (TCP/UDP, incoming/outgoing/both), enable/disable the firewall, view effective configuration, status and rejected-packet journal. Pure GTK4 — works on COSMIC, GNOME, KDE Plasma, XFCE, sway...
- **Applet** (`cosmic-applet-firewall`): COSMIC panel applet, shield icon — green = active, red = disabled. Click opens the GUI. Optional.
- **Declarative**: the GUI writes `firewall-ports.json`, the NixOS module imports it. Apply with `nixos-rebuild` (validated build, then sudo switch from a terminal).

## Install

### 1. Add the flake input

```nix
# flake.nix
{
  inputs.nixos-firewall.url = "github:Swam-web/nixos-firewall";
}
```

### 2. Import the module

```nix
# your NixOS configuration
{ inputs, ... }: {
  imports = [ inputs.nixos-firewall.nixosModules.default ];

  programs.nixos-firewall = {
    enable = true;
    flake = ./.;        # your flake (or any path like /etc/nixos)
    host = "myhost";    # nixosConfigurations.<host>
  };
}
```

- **flake**: where your NixOS configuration lives. `./.` works inside a flake, or use an absolute path.
- **host**: the attribute name of your machine in `nixosConfigurations` (the one you use in `nixos-rebuild switch --flake .#myhost`). If omitted, the machine's hostname is used.

The COSMIC applet is enabled by default — set `applet.enable = false` if you don't use COSMIC.

### 3. Rebuild

```sh
nixos-rebuild switch --flake .#myhost
```

The application appears in your app launcher as **Firewall Manager** (and in the COSMIC panel as a shield icon).

## Try it without installing

```sh
nix run github:Swam-web/nixos-firewall#firewall-gui
```

Standalone mode: the GUI reads `FIREWALL_FLAKE`/`FIREWALL_HOST` environment variables, and falls back to auto-detection (`/etc/nixos`, then the machine hostname) — so it also works launched outside the module.

## How it works

1. **Add a port/range** in the GUI (protocol, direction incoming/outgoing/both, description).
2. The entry is saved in `<flake>/modules/firewall-ports.json` (path configurable via `firewallJsonFile`).
3. **Validate build** (no sudo) — `nixos-rebuild build` checks the configuration.
4. **Apply** — opens a terminal with `sudo nixos-rebuild switch`.
5. The NixOS module imports the JSON: `dir: "in"` entries feed `networking.firewall` (native NixOS options), `out`/`both` entries go to a dedicated nftables output table.

The firewall stays **declarative**: the GUI never touches runtime state, it edits the source of truth and rebuilds.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `programs.nixos-firewall.enable` | `false` | Enable the module |
| `programs.nixos-firewall.flake` | auto-detected | Path of your NixOS flake |
| `programs.nixos-firewall.host` | machine hostname | Flake host (`nixosConfigurations.<host>`) |
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
