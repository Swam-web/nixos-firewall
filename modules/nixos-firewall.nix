# ==============================================================================
# NixOS Firewall — module NixOS
#
# GUI GTK4 + applet COSMIC pour le pare-feu déclaratif NixOS.
#
# Usage :
#   inputs.nixos-firewall.url = "github:Swam-web/nixos-firewall";
#   imports = [ inputs.nixos-firewall.nixosModules.default ];
#   programs.nixos-firewall = {
#     enable = true;
#     # flake et host sont OPTIONNELS — auto-détectés :
#     #   flake : /etc/nixos si présent, sinon chemin du flake courant
#     #   host  : nom d'hôte de la machine
#     flake = ./.;        # optionnel
#     host = "myhost";    # optionnel
#     applet.enable = true;
#   };
#
# Le GUI écrit les ports dans <flake>/modules/firewall-ports.json, que ce
# module importe (option firewallJsonFile surchargeable). Chaque entrée :
#   { port | from+to, desc, dir }  avec dir = "in" | "out" | "both"
# "in" → networking.firewall natif ; "out"/"both" → table nftables dédiée.
# ==============================================================================
{ config, lib, pkgs, ... }:

let
  cfg = config.programs.nixos-firewall;

  # --- Auto-détection (l'utilisateur n'a RIEN à configurer) -------------------
  # flake : option explicite > /etc/nixos (emplacement standard)
  flakeAuto =
    if cfg.flake != null then toString cfg.flake
    else "/etc/nixos";
  # host : option explicite > nom d'hôte de la machine (config.networking.hostName)
  hostAuto =
    if cfg.host != null then cfg.host
    else if config.networking.hostName != "" then config.networking.hostName
    else "localhost";

  flakeDir = flakeAuto;
  defaultJson = flakeDir + "/modules/firewall-ports.json";
  jsonFile = if cfg.firewallJsonFile != null then cfg.firewallJsonFile else defaultJson;

  customPorts =
    if builtins.pathExists jsonFile
    then builtins.fromJSON (builtins.readFile jsonFile)
    else { enable = true; tcp = [ ]; udp = [ ]; tcpRanges = [ ]; udpRanges = [ ]; };

  dirOf = e: e.dir or "in";
  isIn = e: dirOf e != "out";    # in + both
  isOut = e: dirOf e != "in";    # out + both

  # --- ENTRÉE : options natives networking.firewall --------------------------
  inTcp = builtins.filter isIn (customPorts.tcp or [ ]);
  inUdp = builtins.filter isIn (customPorts.udp or [ ]);
  inTcpRanges = builtins.filter isIn (customPorts.tcpRanges or [ ]);
  inUdpRanges = builtins.filter isIn (customPorts.udpRanges or [ ]);

  customTcp = map (e: e.port) inTcp;
  customUdp = map (e: e.port) inUdp;
  customTcpRanges = map (e: { inherit (e) from to; }) inTcpRanges;
  customUdpRanges = map (e: { inherit (e) from to; }) inUdpRanges;

  # --- SORTIE : table nftables dédiée ----------------------------------------
  nftDport = e:
    if e ? port
    then toString e.port
    else "${toString e.from}-${toString e.to}";

  outLines = proto: entries:
    lib.concatMapStringsSep "\n        "
      (e: "${proto} dport ${nftDport e} accept")
      (builtins.filter isOut entries);

  outEntries = {
    tcp = outLines "tcp" (customPorts.tcp or [ ]);
    tcpRanges = outLines "tcp" (customPorts.tcpRanges or [ ]);
    udp = outLines "udp" (customPorts.udp or [ ]);
    udpRanges = outLines "udp" (customPorts.udpRanges or [ ]);
  };

  hasOutRules =
    outEntries.tcp != "" || outEntries.udp != ""
    || outEntries.tcpRanges != "" || outEntries.udpRanges != "";

  outRuleset = ''
    chain output {
      type filter hook output priority 100; policy accept;
      # ${"Outgoing ports managed by nixos-firewall (dir out/both)"}
      ${outEntries.tcp}
      ${outEntries.tcpRanges}
      ${outEntries.udp}
      ${outEntries.udpRanges}
    }
  '';

  # Wrapper fixant l'environnement (flake/hôte/JSON) pour GUI et applet.
  # IMPORTANT : heredoc NON quoté → les variables nix ${pkg} sont substituées
  # au build ; les variables runtime utilisent \$ pour arriver au shell.
  envWrapper = pkg:
    pkgs.runCommand "${pkg.name or pkg.pname or "env"}-wrapped" { }
      ''
        mkdir -p $out/bin
        for exe in ${pkg}/bin/*; do
          name=$(basename "$exe")
          cat > $out/bin/$name <<'INNER'
      #!/bin/sh
      export FIREWALL_FLAKE="${flakeDir}"
      export FIREWALL_HOST="${hostAuto}"
      export FIREWALL_JSON="${toString jsonFile}"
      exec "${pkg}/bin/SCRIPT_NAME" "$@"
      INNER
          sed -i "s|SCRIPT_NAME|$name|" $out/bin/$name
          chmod +x $out/bin/$name
        done
        ln -s ${pkg}/share $out/share 2>/dev/null || true
      '';

  # Paquets : options `package` / `package-applet` (fixées par le flake),
  # sinon recettes locales de ce flake.
  guiPkg = cfg.package;
  appletPkg = cfg.package-applet;
in
{
  options.programs.nixos-firewall = {
    enable = lib.mkEnableOption "NixOS Firewall (GTK4 manager + COSMIC applet)";

    flake = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      example = ./.;
      description = ''
        Path of your NixOS flake (for nix eval / nixos-rebuild).
        Optional — auto-detected when null: /etc/nixos if present.
      '';
    };

    host = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "myhost";
      description = ''
        Host attribute of your flake (nixosConfigurations.<host>).
        Optional — auto-detected when null: this machine's hostname
        (config.networking.hostName).
      '';
    };

    firewallJsonFile = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      description = "Custom path for the GUI-written ports JSON (default: <flake>/modules/firewall-ports.json).";
    };

    applet.enable = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Install the COSMIC panel applet (works on COSMIC only).";
    };

    package = lib.mkOption {
      type = lib.types.package;
      description = "firewall-gui package (defaults to this flake's).";
    };

    package-applet = lib.mkOption {
      type = lib.types.package;
      description = "cosmic-applet-firewall package (defaults to this flake's).";
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages =
      [ (envWrapper guiPkg) ]
      ++ lib.optionals cfg.applet.enable [ (envWrapper appletPkg) ];

    networking.firewall = {
      # Interrupteur activer/désactiver piloté par le GUI (mkForce : priorité
      # sur un enable défini ailleurs).
      enable = lib.mkForce (customPorts.enable or true);

      allowedTCPPorts = customTcp;
      allowedUDPPorts = customUdp;
      allowedTCPPortRanges = customTcpRanges;
      allowedUDPPortRanges = customUdpRanges;
    };

    # SORTIE (dir "out" / "both") — table nftables dédiée, policy accept :
    # inoffensive tant que la sortie n'est pas filtrée ; ces "accept"
    # explicites deviennent utiles si une policy drop est posée sur output.
    networking.nftables.tables.nixos-firewall-out = lib.mkIf hasOutRules {
      family = "inet";
      content = outRuleset;
    };
  };
}
