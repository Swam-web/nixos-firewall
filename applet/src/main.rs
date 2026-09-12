// SPDX-License-Identifier: GPL-3.0-only
//! Applet COSMIC « Statut pare-feu »
//! Bouclier vert si le pare-feu est actif, rouge s'il est désactivé.
//! Clic : ouvre « Gestion du pare-feu » (firewall-gui-launcher).

mod app;

fn main() {
    cosmic::applet::run::<app::FirewallApplet>(());
}
