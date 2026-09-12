{
  description = "NixOS Firewall — GTK4 manager + COSMIC applet for the NixOS declarative firewall";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = forAllSystems (pkgs: rec {
        firewall-gui = pkgs.callPackage ./nix/firewall-gui.nix { };
        cosmic-applet-firewall = pkgs.callPackage ./nix/cosmic-applet-firewall.nix { };
        default = firewall-gui;
      });

      nixosModules.default = {
        imports = [ ./modules/nixos-firewall.nix ];
        programs.nixos-firewall = {
          package = self.packages.x86_64-linux.firewall-gui;
          package-applet = self.packages.x86_64-linux.cosmic-applet-firewall;
        };
      };

      apps = forAllSystems (pkgs: {
        default = {
          type = "app";
          program = "${self.packages.${pkgs.system}.firewall-gui}/bin/firewall-gui";
        };
      });
    };
}
