{ lib
, stdenv
, python3
, glib
, gtk4
, gdk-pixbuf
, graphene
, harfbuzz
, pango
, gobject-introspection
, wrapGAppsHook4
}:

# GUI GTK4 de gestion du pare-feu NixOS (déclaratif).
# - Lectures : `nix eval` sur le flake courant
# - Écriture : JSON de ports consommé par le module NixOS
# - Flake/hôte paramétrables : FIREWALL_FLAKE / FIREWALL_HOST (env, fixés
#   par le module NixOS) — aucune valeur en dur.

stdenv.mkDerivation {
  pname = "firewall-gui";
  version = "1.0.0";

  src = ../gui;

  dontBuild = true;

  nativeBuildInputs = [ wrapGAppsHook4 ];
  buildInputs = [
    glib
    gtk4
    gdk-pixbuf
    graphene
    harfbuzz
    pango
    gobject-introspection
  ];

  pythonEnv = python3.withPackages (ps: with ps; [ pygobject3 ]);

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin $out/share/applications $out/share/icons/hicolor/scalable/apps

    cp app.py $out/libexec-firewall-gui.py
    install -Dm644 firewall-gui.svg $out/share/icons/hicolor/scalable/apps/firewall-gui.svg

    cat > $out/bin/firewall-gui <<EOF
    #!/bin/sh
    exec $pythonEnv/bin/python $out/libexec-firewall-gui.py "\$@"
    EOF
    chmod +x $out/bin/firewall-gui

    cat > $out/share/applications/firewall-gui.desktop <<EOF
    [Desktop Entry]
    Type=Application
    Name=Firewall Manager
    Name[fr]=Gestion du pare-feu
    Comment=NixOS firewall ports, status and journal
    Comment[fr]=Ports, statut et journal du pare-feu NixOS
    Exec=firewall-gui
    Icon=firewall-gui
    Categories=System;Network;
    Keywords=firewall;nftables;ports;pare-feu;
    EOF

    runHook postInstall
  '';

  meta = {
    description = "GTK4 manager for the NixOS declarative firewall (ports, status, journal)";
    homepage = "https://github.com/Swam-web/nixos-firewall";
    license = lib.licenses.gpl3Only;
    mainProgram = "firewall-gui";
    platforms = lib.platforms.linux;
  };
}
