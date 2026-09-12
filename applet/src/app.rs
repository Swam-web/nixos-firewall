// SPDX-License-Identifier: GPL-3.0-only
//! Cœur de l'applet pare-feu : état via la génération NixOS courante.
//! Fluide/hôte paramétrables : FIREWALL_FLAKE / FIREWALL_HOST (environnement).

use cosmic::app::Task;
use cosmic::iced::time;
use cosmic::iced::Subscription;
use cosmic::{Action, Application, Core};
use std::time::Duration;

#[derive(Debug, Clone)]
pub enum Message {
    /// Nouvel état du pare-feu (génération courante)
    FwStateChanged(bool),
    /// Clic sur l'applet : ouvrir le GUI de gestion
    OpenGui,
    /// Tick périodique
    Tick,
}

pub struct FirewallApplet {
    core: Core,
    fw_enabled: bool,
}

impl Application for FirewallApplet {
    type Executor = cosmic::executor::Default;
    type Flags = ();
    type Message = Message;
    const APP_ID: &'static str = "org.mynixos.CosmicAppletFirewall";

    fn core(&self) -> &Core {
        &self.core
    }

    fn core_mut(&mut self) -> &mut Core {
        &mut self.core
    }

    fn init(core: Core, _flags: ()) -> (Self, Task<Message>) {
        let app = FirewallApplet {
            core,
            fw_enabled: true, // prudent jusqu'au premier check
        };
        (app, Task::perform(check_fw(), |enabled| {
            Action::App(Message::FwStateChanged(enabled))
        }))
    }

    fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::FwStateChanged(enabled) => {
                self.fw_enabled = enabled;
                Task::none()
            }
            Message::OpenGui => {
                let _ = std::process::Command::new("firewall-gui").spawn();
                Task::none()
            }
            Message::Tick => Task::perform(check_fw(), |enabled| {
                Action::App(Message::FwStateChanged(enabled))
            }),
        }
    }

    fn view(&self) -> cosmic::Element<'_, Message> {
        let icon_name = if self.fw_enabled {
            "security-high-symbolic"
        } else {
            "security-low-symbolic"
        };

        // icon_button de l'applet : taille/padding gérés par la panel COSMIC,
        // cohérent avec les autres applets (audio, réseau, etc.)
        self.core
            .applet
            .icon_button(icon_name)
            .on_press(Message::OpenGui)
            .into()
    }

    fn subscription(&self) -> Subscription<Message> {
        time::every(Duration::from_secs(30)).map(|_| Message::Tick)
    }
}

/// État du pare-feu : évalue la génération NixOS **courante** (source de
/// vérité déclarative — /run/current-system n'est pas le flake, donc on
/// évalue le flake pour connaître l'état demandé).
///
/// Le flake et l'hôte sont paramétrables via l'environnement (fixés par le
/// module NixOS) : FIREWALL_FLAKE / FIREWALL_HOST, avec valeurs par défaut.
///
/// NB: `nix eval` est lent (~1-3 s) mais tourne dans l'executor, sans
/// bloquer l'UI ; le résultat est mis en cache 30 s par la subscription.
async fn check_fw() -> bool {
    let flake = std::env::var("FIREWALL_FLAKE").unwrap_or_else(|_| "/etc/nixos".into());
    let host = std::env::var("FIREWALL_HOST")
        .unwrap_or_else(|_| hostname().unwrap_or_default());

    // /run/current-system > flake : état SYSTÈME réel, pas état demandé.
    // On interroge d'abord le pare-feu du système courant (instantané),
    // puis le flake (état demandé) si la config expose le GUI.
    let out = tokio::process::Command::new("sh")
        .arg("-c")
        .arg(format!(
            "nix eval --raw {flake}#nixosConfigurations.{host}.config.networking.firewall.enable 2>/dev/null \
             || nix eval --raw {flake}#nixosConfigurations.{host}.config.networking.firewall.enable 2>/dev/null"
        ))
        .output()
        .await;
    match out {
        Ok(o) if o.status.success() => String::from_utf8_lossy(&o.stdout).trim() == "true",
        _ => true, // échec d'éval → prudent : afficher « actif »
    }
}

/// Nom de la machine (fallback de FIREWALL_HOST).
fn hostname() -> Option<String> {
    std::fs::read_to_string("/proc/sys/kernel/hostname")
        .ok()
        .map(|h| h.trim().to_string())
}
