# NixOS Firewall

**GTK4 manager + COSMIC applet** for the [NixOS](https://nixos.org) declarative firewall.

- **GUI** (`firewall-gui`): manage ports/ranges (TCP/UDP, incoming/outgoing/both), enable/disable the firewall, view effective configuration, status and rejected-packet journal. Pure GTK4 — works on COSMIC, GNOME, KDE Plasma, XFCE, sway...
- **Applet** (`cosmic-applet-firewall`): COSMIC panel applet, shield icon — green = active, red = disabled. Click opens the GUI. Optional.
- **Declarative**: the GUI writes `firewall-ports.json`, the NixOS module imports it. Apply with `nixos-rebuild`.

## Install — copy & paste

### 1. In `flake.nix`, add the input and the module

```nix
{
  # ... your existing inputs ...
  inputs.nixos-firewall = {
    url = "github:Swam-web/nixos-firewall";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, nixos-firewall, ... }@inputs: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ./configuration.nix
        nixos-firewall.nixosModules.default   # <-- add this line
      ];
    };
  };
}
```

### 2. In your NixOS configuration, enable it

```nix
{
  programs.nixos-firewall.enable = true;
}
```

That's all — done.

### 3. Rebuild and switch

```sh
sudo nixos-rebuild switch --flake .#myhost
```

The app appears in your launcher as **Firewall Manager**, and the shield applet in the COSMIC panel.

## How it works

1. **Add a port or range** in the GUI (protocol, direction: incoming / outgoing / both, description).
2. The entry is saved in `<flake>/modules/firewall-ports.json`.
3. **Validate build** (no sudo) — checks the configuration.
4. **Apply** — opens a terminal with the sudo rebuild command.
5. On rebuild, the module imports the JSON: `incoming` feeds the native `networking.firewall`, `outgoing`/`both` go to a dedicated nftables output table.

The firewall stays fully declarative — the GUI never touches runtime state, it edits the source of truth and rebuilds.

## Options (all optional)

| Option | Default | Description |
|--------|---------|-------------|
| `enable` | `false` | Enable the module |
| `flake` | `/etc/nixos` | Your NixOS flake path — **set it only if your config lives elsewhere** |
| `host` | machine hostname | `nixosConfigurations.<host>` — only if different from your hostname |
| `applet.enable` | `true` | COSMIC panel applet (set `false` on GNOME/KDE) |
| `firewallJsonFile` | `<flake>/modules/firewall-ports.json` | Custom JSON path |

Example — config outside `/etc/nixos`, hostname different from flake attribute:

```nix
programs.nixos-firewall = {
  enable = true;
  flake = "/persist/nixos";
  host = "myhost";
  applet.enable = false;   # not on COSMIC
};
```

## Try it without installing

```sh
nix run github:Swam-web/nixos-firewall#firewall-gui
```

## Packages

```sh
nix build github:Swam-web/nixos-firewall#firewall-gui
nix build github:Swam-web/nixos-firewall#cosmic-applet-firewall
```

## Languages

The GUI follows the system language automatically: **français / English** (add a dict in `gui/app.py` for more).

## License

GPL-3.0-only
