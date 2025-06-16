import os
import json
import hmac
import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, GLib, AppIndicator3, Notify

INTERVAL = 30
TZ = ZoneInfo("Europe/Minsk")
CONFIG_DIR = os.path.expanduser("~/.config/code_generator")
CONFIG_PATH = os.path.join(CONFIG_DIR, "secret.json")
APPEND = "OLEG"  # <<<<<<<---------------- добавленное секретное слово


class TrayApp:
    def __init__(self):
        self.last_secret = ""
        self.last_code = "—"
        self.time_left = INTERVAL
        self.notifications_enabled = True
        self.code_visible = True  # Переменная для отслеживания видимости кода

        Notify.init("Генератор кода")
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.load_secret()

        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "logo.png"))
        self.ind = AppIndicator3.Indicator.new(
            "code-generator", icon_path,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        menu = Gtk.Menu()
        self.code_item = Gtk.MenuItem(label=self._code_label())
        self.code_item.set_sensitive(False)
        menu.append(self.code_item)
        menu.append(Gtk.SeparatorMenuItem())

        set_key = Gtk.MenuItem(label="Ключ‑слово")
        set_key.connect("activate", self.on_input)
        menu.append(set_key)
        menu.append(Gtk.SeparatorMenuItem())

        self.notify_toggle = Gtk.CheckMenuItem(label="Уведомления")
        self.notify_toggle.set_active(self.notifications_enabled)
        self.notify_toggle.connect("toggled", self.on_toggle_notifications)
        menu.append(self.notify_toggle)

        toggle_code_item = Gtk.CheckMenuItem(label="Отображение")
        toggle_code_item.set_active(self.code_visible)
        toggle_code_item.connect("toggled", self.on_toggle_code_visibility)
        menu.append(toggle_code_item)
        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Выход")
        quit_item.connect("activate", Gtk.main_quit)
        menu.append(quit_item)
        menu.show_all()
        self.ind.set_menu(menu)
        GLib.timeout_add_seconds(1, self.tick)

    def _code_label(self):
        return f"Код: {self.last_code}    ⏳{self.time_left}s"

    def load_secret(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.last_secret = data.get("secret", "")
                self.notifications_enabled = data.get("notifications_enabled", True)
        except FileNotFoundError:
            pass

    def save_secret(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "secret": self.last_secret,
                "notifications_enabled": self.notifications_enabled
            }, f, ensure_ascii=False, indent=2)

    def on_toggle_notifications(self, widget):
        self.notifications_enabled = widget.get_active()
        self.save_secret()

    def on_input(self, _):
        dialog = Gtk.Dialog(title="Ключ‑слово")
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        entry = Gtk.Entry()
        entry.set_text(self.last_secret)
        dialog.get_content_area().add(entry)
        dialog.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            secret = entry.get_text().strip()
            if secret and secret != self.last_secret:
                self.last_secret = secret
                self.save_secret()
                self.update_code(force=True)
        dialog.destroy()

    def on_toggle_code_visibility(self, widget):
        self.code_visible = widget.get_active()
        self.update_code(force=True)  # Перезапускаем обновление, чтобы показать/скрыть код
        self.save_secret()

    def tick(self):
        if not self.last_secret:
            return True
        self.update_code()
        return True

    def update_code(self, force=False):
        now = datetime.now(TZ)
        t_sec = int(now.astimezone(timezone.utc).timestamp())
        self.time_left = INTERVAL - (t_sec % INTERVAL)
        code = self.generate_code(self.last_secret)
        changed = (code != self.last_code)
        self.last_code = code
        self.code_item.set_label(self._code_label())

        if self.code_visible:
            self.ind.set_label(f" {self.last_code}    ⏳{self.time_left}", "")  # Отображаем код в трее
        else:
            self.ind.set_label(" ", "")  # Скрываем код в трее

        if (changed and not force or force) and self.notifications_enabled:
            self.show_notification(code)

    def generate_code(self, secret, digits=6):
        now = datetime.now(TZ)
        slot = int(now.astimezone(timezone.utc).timestamp()) // INTERVAL
        msg = f"{secret}:{APPEND}:{slot}".encode()
        hm = hmac.new(secret.encode(), msg, hashlib.sha256).digest()
        return f"{int.from_bytes(hm[:4], 'big') % (10 ** digits):0{digits}d}"

    def show_notification(self, code):
        if not self.notifications_enabled:
            return
        title = "Код обновлён: " + code
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "logo.png"))
        notification = Notify.Notification.new(title, icon=icon_path)
        notification.show()


def main():
    TrayApp()
    Gtk.main()


if __name__ == "__main__":
    main()
