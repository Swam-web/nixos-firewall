{ lib
, stdenv
, rustPlatform
, just
, pkg-config
, libxkbcommon
, wayland
, wayland-scanner
, libcosmicAppHook
, libclang
, glibc
}:

# Applet COSMIC « statut pare-feu » : bouclier vert = actif, rouge = off.
# Clic : ouvre firewall-gui. Fluide/hôte paramétrables via FIREWALL_FLAKE /
# FIREWALL_HOST (environnement, fixés par le module NixOS).

rustPlatform.buildRustPackage {
  pname = "cosmic-applet-firewall";
  version = "1.0.0";

  src = ../applet;

  cargoHash = "sha256-HaoueCuq/N3KUS2osWUfeCeg2VHs8t88IIIDTPH3MAY=";

  nativeBuildInputs = [
    just
    libcosmicAppHook
    pkg-config
  ];

  buildInputs = [
    libxkbcommon
    wayland
    wayland-scanner
  ];

  env.BINDGEN_EXTRA_CLANG_ARGS = "-I${libclang.lib}/lib -I${glibc.dev}/include";

  dontUseJustBuild = true;
  dontUseJustCheck = true;
  justFlags = [
    "--set"
    "prefix"
    (placeholder "out")
    "--set"
    "bin-src"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}/release/cosmic-applet-firewall"
  ];

  meta = {
    description = "COSMIC applet showing firewall status (green = active, red = disabled)";
    homepage = "https://github.com/Swam-web/nixos-firewall";
    license = lib.licenses.gpl3Only;
    mainProgram = "cosmic-applet-firewall";
    platforms = lib.platforms.linux;
  };
}
