#!/usr/bin/env python3
# =============================================================================
# PROJECT:      SteamMachine-DIY - Control Center
# VERSION:      1.0.0
# DESCRIPTION:  PyQt6 Dashboard for SteamOS-DIY with Search functionality.
# PHILOSOPHY:   KISS (Keep It Simple, Stupid)
# REPOSITORY:   https://github.com/dlucca1986/SteamMachine-DIY
# PATH:         /usr/local/lib/steamos_diy/control_center.py
# LICENSE:      MIT
# =============================================================================

from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QPlainTextEdit,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QPainter,
)
from PyQt6.QtCore import (
    QRegularExpression,
    Qt,
    QTimer,
    pyqtSignal,
    QRect,
    QSize,
)
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

from io import StringIO
from ruamel.yaml import YAML

# Initialize the Round-Trip YAML parser
# This ensures comments, indentation, and quotes are preserved.
yaml_parser = YAML()
yaml_parser.preserve_quotes = True
yaml_parser.indent(mapping=2, sequence=4, offset=2)
yaml_parser.width = 4096  # Avoid unexpected line wrapping

# pylint: disable=no-name-in-module


# pylint: disable=too-few-public-methods
class LineNumberArea(QWidget):
    """Side area widget to render line numbers."""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class YAMLEditor(QPlainTextEdit):
    """Enhanced editor with line numbers and auto-indentation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def line_number_area_width(self):
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val /= 10
            digits += 1
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(
                cr.left(), cr.top(), self.line_number_area_width(), cr.height()
            )
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(
            event.rect(), QColor("#2c3e50")
        )  # Colore barra laterale
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(
            self.blockBoundingGeometry(block)
            .translated(self.contentOffset())
            .top()
        )
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#95a5a6"))  # Colore numeri
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            line_text = cursor.block().text()
            indent = re.match(r"^\s*", line_text).group(0)
            super().keyPressEvent(event)
            self.insertPlainText(indent)
        else:
            super().keyPressEvent(event)


class YAMLSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for YAML."""

    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        self._setup_rules()

    def _setup_rules(self):
        """Define the highlighting rules."""
        # 1. Comments (Grey)
        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#7f8c8d"))
        self.rules.append((QRegularExpression(r"#.*"), comment_fmt))

        # 2. Keys (Blue)
        key_fmt = QTextCharFormat()
        key_fmt.setForeground(QColor("#3498db"))
        key_fmt.setFontWeight(QFont.Weight.Bold)
        self.rules.append((QRegularExpression(r"^\s*[\w.-]+(?=:)"), key_fmt))

        # 3. Quoted Strings (Yellow)
        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor("#f1c40f"))
        self.rules.append((QRegularExpression(r'"[^"]*"'), str_fmt))
        self.rules.append((QRegularExpression(r"'[^']*'"), str_fmt))

        # 4. Lists (Green)
        val_fmt = QTextCharFormat()
        val_fmt.setForeground(QColor("#27ae60"))
        self.rules.append((QRegularExpression(r"^\s*-\s.*"), val_fmt))

        # 5. Numbers (Orange)
        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor("#e67e22"))
        self.rules.append((QRegularExpression(r"\b\d+\b"), num_fmt))

        # 6. Symbols (Red)
        sym_fmt = QTextCharFormat()
        sym_fmt.setForeground(QColor("#e74c3c"))
        sym_fmt.setFontWeight(QFont.Weight.Bold)
        self.rules.append((QRegularExpression(r"[:\-]"), sym_fmt))

    # pylint: disable=invalid-name
    def highlightBlock(self, text):
        """Apply rules to the text block."""
        for expression, fmt in self.rules:
            match_iterator = expression.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(
                    match.capturedStart(), match.capturedLength(), fmt
                )


class LogFilter:
    """
    Utility to filter redundant log messages and sanitize strings.
    Limits repeated messages to a specific threshold.
    """

    def __init__(self, limit=2):
        self.limit = limit
        self.history = {}

    def is_redundant(self, message):
        """
        Check if a message has exceeded the repetition limit.
        Sanitizes timestamps and PIDs to identify the core message.
        """
        # Remove timestamps (e.g., Feb 20 11:11:53) and PIDs (e.g., [1234])
        core = re.sub(r"^[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2}", "", message)
        core = re.sub(r"\[\d+\]", "[]", core).strip()

        count = self.history.get(core, 0)
        if count < self.limit:
            self.history[core] = count + 1
            return False
        return True

    def reset(self):
        """Clear the message history."""
        self.history.clear()


# pylint: disable=too-many-instance-attributes
class SDYControlCenter(QMainWindow):
    """Main application window for SteamMachine-DIY control."""

    process_finished = pyqtSignal(str, str, bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SteamMachine-DIY Control Center")
        self.resize(1000, 700)

        self.lib_path = "/usr/local/lib/steamos_diy"
        self.conf_root = Path(os.path.expanduser("~/.config/steamos_diy"))

        self.log_filter = LogFilter(limit=2)

        # UI components
        self.diag_tab = self.maint_tab = self.global_tab = None
        self.games_tab = self.tabs = self.log_display = None
        self.tag_filter = self.copy_btn = self.support_btn = None
        self.global_editor = self.combo_global_files = None
        self.global_temp_btn = self.global_save_btn = self.combo_games = None
        self.game_editor = self.game_temp_btn = self.game_save_btn = None
        self.global_hl = self.game_hl = None

        self.view_states = {
            "global": {"is_template": False, "cache": ""},
            "games": {"is_template": False, "cache": ""},
        }

        self._setup_ui()
        self.process_finished.connect(self._show_completion_message)
        # Connect textChanged signal to clear highlights immediately when
        # typing
        self.global_editor.textChanged.connect(
            lambda: self.global_editor.setExtraSelections([])
        )
        self.game_editor.textChanged.connect(
            lambda: self.game_editor.setExtraSelections([])
        )

    def _setup_ui(self):
        """UI Setup and Tab assembly."""
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.setCentralWidget(self.tabs)

        self.init_diag_tab()
        self.init_maint_tab()
        self.init_global_tab()
        self.init_games_tab()

        self.tabs.addTab(self.diag_tab, "Diagnostics")
        self.tabs.addTab(self.maint_tab, "Maintenance")
        self.tabs.addTab(self.global_tab, "Global Options")
        self.tabs.addTab(self.games_tab, "Game Overrides")

    def on_tab_changed(self, index):
        """Handle tab switching."""
        if index == 0:
            self.load_logs()

    def init_diag_tab(self):
        """Initialize the diagnostics tab."""
        self.diag_tab = QWidget()
        layout = QVBoxLayout()
        header = QHBoxLayout()
        self.tag_filter = QComboBox()
        self.tag_filter.addItems(
            [
                "ALL",
                "SELECT",
                "SDY",
                "LAUNCH",
                "GAMESCOPE",
                "ENGINE",
                "STEAM",
                "PROF",
                "BRANCH-SHIM",
            ]
        )
        self.tag_filter.currentTextChanged.connect(self.load_logs)
        header.addWidget(QLabel("<b>Filter logs by component:</b>"))
        header.addWidget(self.tag_filter)
        header.addStretch()
        layout.addLayout(header)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Monospace", 10))
        layout.addWidget(self.log_display)

        footer = QHBoxLayout()
        self.copy_btn = QPushButton("📋 Copy to Clipboard")
        self.copy_btn.clicked.connect(self.copy_logs)
        self.support_btn = QPushButton("🛠️ Export Support Log")
        self.support_btn.clicked.connect(self.export_support_log)
        footer.addWidget(self.copy_btn)
        footer.addWidget(self.support_btn)
        footer.addStretch()
        layout.addLayout(footer)
        self.diag_tab.setLayout(layout)

    def init_maint_tab(self):
        """Initialize the maintenance tab."""
        self.maint_tab = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        btn_style = "height: 40px; text-align: left; padding-left: 15px;"

        # The session_select script already handles both the SSoT file
        # write and the Plasma logout logic.
        tools = [
            (
                "🎮 Switch to Steam (Game Mode)",
                lambda: self._safe_spawn(
                    [
                        "python3",
                        os.path.join(self.lib_path, "session_select.py"),
                        "steam",
                    ]
                ),
            ),
            ("📦 Create Full System Backup", self.run_backup),
            ("🔄 Restore from Archive", self.run_restore),
            (
                "🖥️ Open Konsole Terminal",
                lambda: self._safe_spawn(["konsole"]),
            ),
            (
                "📂 Browse Config Folder",
                lambda: self._safe_spawn(["xdg-open", str(self.conf_root)]),
            ),
            (
                "ℹ️ System Information",
                lambda: self._safe_spawn(["kinfocenter"]),
            ),
        ]

        layout.addWidget(QLabel("<b>System Management</b>"))
        for text, func in tools:
            btn = QPushButton(text)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(func)
            layout.addWidget(btn)
        self.maint_tab.setLayout(layout)

    def _safe_spawn(self, cmd):
        """Internal helper to spawn processes."""
        with subprocess.Popen(cmd) as _:
            pass

    def init_global_tab(self):
        """Initialize the global config tab."""
        self.global_tab = QWidget()
        layout = QVBoxLayout()
        header = QHBoxLayout()
        self.combo_global_files = QComboBox()
        self.combo_global_files.addItems(
            ["config.yaml", "config.example.yaml", "gamescope.example.yaml"]
        )
        self.combo_global_files.currentTextChanged.connect(
            self.load_global_file
        )
        header.addWidget(QLabel("<b>Target File:</b>"))
        header.addWidget(self.combo_global_files, 1)
        layout.addLayout(header)

        self.global_editor = YAMLEditor()
        self.global_editor.setFont(QFont("Monospace", 10))
        self.global_hl = YAMLSyntaxHighlighter(self.global_editor.document())
        layout.addWidget(self.global_editor)

        btns = QHBoxLayout()
        self.global_temp_btn = QPushButton("📄 View Template")
        self.global_temp_btn.clicked.connect(
            lambda: self.toggle_template("global")
        )

        g_fix_btn = QPushButton("🪄 Beautify")
        g_fix_btn.clicked.connect(
            lambda: self.beautify_yaml(self.global_editor)
        )

        self.global_save_btn = QPushButton("💾 Save Configuration")
        self.global_save_btn.clicked.connect(self.save_global_config)

        btns.addWidget(self.global_temp_btn)
        btns.addWidget(g_fix_btn)
        btns.addStretch()
        btns.addWidget(self.global_save_btn)
        layout.addLayout(btns)
        self.global_tab.setLayout(layout)
        self.load_global_file()

    def init_games_tab(self):
        """Initialize the game overrides tab."""
        self.games_tab = QWidget()
        layout = QVBoxLayout()
        header = QHBoxLayout()
        self.combo_games = QComboBox()
        self.combo_games.setEditable(True)
        self.combo_games.currentTextChanged.connect(self.load_game_file)
        btn_scan = QPushButton("🔍 Scan History")
        btn_scan.clicked.connect(self.refresh_detected_games)
        header.addWidget(QLabel("<b>Game ID:</b>"))
        header.addWidget(self.combo_games, 1)
        header.addWidget(btn_scan)
        layout.addLayout(header)

        self.game_editor = YAMLEditor()
        self.game_editor.setFont(QFont("Monospace", 10))
        self.game_hl = YAMLSyntaxHighlighter(self.game_editor.document())
        layout.addWidget(self.game_editor)

        btns = QHBoxLayout()
        self.game_temp_btn = QPushButton("📄 View Template")
        self.game_temp_btn.clicked.connect(
            lambda: self.toggle_template("games")
        )

        game_fix_btn = QPushButton("🪄 Beautify")
        game_fix_btn.clicked.connect(
            lambda: self.beautify_yaml(self.game_editor)
        )

        self.game_save_btn = QPushButton("💾 Save Game Profile")
        self.game_save_btn.clicked.connect(self.save_game_profile)

        btns.addWidget(self.game_temp_btn)
        btns.addWidget(game_fix_btn)
        btns.addStretch()
        btns.addWidget(self.game_save_btn)
        layout.addLayout(btns)
        self.games_tab.setLayout(layout)

    def beautify_yaml(self, editor):
        """
        Attempts to fix common YAML issues on the fly (Tabs, spaces)
        and realigns syntax using ruamel.yaml round-trip.
        """
        try:
            raw_text = editor.toPlainText()
            if not raw_text.strip():
                return

            # --- ON THE FLY FIXES ---
            # 1. Replace Tabs with 2 spaces (Tabs are illegal in YAML)
            fixed_text = raw_text.replace("\t", "  ")

            # 2. Strip trailing whitespaces from each line to avoid hidden
            # chars
            fixed_text = "\n".join(
                [line.rstrip() for line in fixed_text.splitlines()]
            )

            # Try to load the sanitized text
            try:
                data = yaml_parser.load(fixed_text)
            except Exception:
                # If it still fails, it's a structural error we can't auto-fix
                raise

            # Dump back to a clean string using the Round-Trip parser
            stream = StringIO()
            yaml_parser.dump(data, stream)
            clean_text = stream.getvalue()

            # Check if changes are actually needed
            if raw_text.strip() == clean_text.strip():
                return

            # Update editor content
            editor.setPlainText(clean_text)

            # Refresh highlighting
            is_global = editor == self.global_editor
            highlighter = self.global_hl if is_global else self.game_hl
            if highlighter:
                highlighter.rehighlight()

        except Exception as err:
            # Handle cases where the YAML is too broken to be auto-fixed
            mark = getattr(err, "problem_mark", None)
            if mark:
                line_idx = mark.line
                column = mark.column
                self._highlight_error_line(editor, line_idx)

                QMessageBox.warning(
                    self,
                    "Alignment Error",
                    f"YAML alignment issue at line {
                        line_idx +
                        1}, col {
                        column +
                        1}.\n"
                    "Check your spaces/indentation!"
                    "This couldn't be auto-fixed.",
                )
            else:
                QMessageBox.warning(
                    self, "Error", f"Could not beautify: {err}"
                )

    def toggle_template(self, context):
        """Toggle between current config and templates."""
        state = self.view_states[context]
        is_global = context == "global"
        editor = self.global_editor if is_global else self.game_editor
        save_btn = self.global_save_btn if is_global else self.game_save_btn
        temp_btn = self.global_temp_btn if is_global else self.game_temp_btn
        hl = self.global_hl if is_global else self.game_hl

        if not state["is_template"]:
            if is_global:
                target = self.combo_global_files.currentText()
                fname = (
                    target
                    if ".example." in target
                    else target.replace(".yaml", ".example.yaml")
                )
                t_path = self.conf_root / fname
            else:
                t_path = self.conf_root / "game.example.yaml"

            if t_path.exists():
                state["cache"] = editor.toPlainText()
                with open(t_path, "r", encoding="utf-8") as f:
                    editor.setPlainText(f.read())
                temp_btn.setText("⬅️ Back to Editor")
                state["is_template"] = True
                save_btn.setEnabled(False)
                hl.rehighlight()
            else:
                QMessageBox.warning(self, "Missing", f"Not found: {t_path}")
        else:
            editor.setPlainText(state["cache"])
            temp_btn.setText("📄 View Template")
            state["is_template"] = False
            save_btn.setEnabled(True)
            hl.rehighlight()

    def _atomic_save(self, path, content, editor):
        """
        Save file atomically with enhanced error reporting and line jumping.
        """
        editor.setExtraSelections([])

        try:
            # Validate YAML using the ruamel parser
            yaml_parser.load(content)

            # Atomic save logic
            path_obj = Path(path)
            tmp = path_obj.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
            os.rename(tmp, path_obj)

            QMessageBox.information(self, "Success", "Configuration saved!")

        except Exception as exc:
            # Extract error location from ruamel exception
            error_msg = f"Invalid YAML syntax: {exc}"
            line_idx = -1

            # ruamel.yaml uses 'context_mark' or 'problem_mark'
            mark = getattr(exc, "problem_mark", None)
            if mark:
                line_idx = mark.line
                error_msg = f"<b>Syntax Error at line {
                        line_idx +
                        1}, column {
                        mark.column +
                        1}:</b><br>" f"<i style='color: #e74c3c;'>{
                        getattr(
                            exc,
                            'problem',
                            'Unknown error')}</i>"

                self._highlight_error_line(editor, line_idx)

                # Move cursor to error line
                cursor = editor.textCursor()
                cursor.movePosition(cursor.MoveOperation.Start)
                for _ in range(line_idx):
                    cursor.movePosition(cursor.MoveOperation.Down)
                editor.setTextCursor(cursor)

            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("YAML Syntax Error")
            msg_box.setText(error_msg)
            msg_box.exec()

        except OSError as err:
            QMessageBox.critical(
                self, "System Error", f"Failed to write file:\n{err}"
            )

    def _highlight_error_line(self, editor, line_idx):
        """
        Highlights the error line and the potential cause line.
        YAML parsers often report the line following an unclosed quote.
        """
        extra_selections = []

        # 1. Primary Error Selection (Red - where the parser stopped)
        error_sel = QTextEdit.ExtraSelection()
        error_color = QColor("#e74c3c")
        error_color.setAlpha(60)
        error_sel.format.setBackground(error_color)
        error_sel.format.setProperty(
            QTextCharFormat.Property.FullWidthSelection, True
        )

        # 2. Potential Cause Selection (Orange - the line above)
        cause_sel = QTextEdit.ExtraSelection()
        cause_color = QColor("#f39c12")
        cause_color.setAlpha(40)
        cause_sel.format.setBackground(cause_color)
        cause_sel.format.setProperty(
            QTextCharFormat.Property.FullWidthSelection, True
        )

        # Position for Primary Error
        error_cursor = editor.textCursor()
        error_cursor.movePosition(error_cursor.MoveOperation.Start)
        for _ in range(line_idx):
            error_cursor.movePosition(error_cursor.MoveOperation.Down)

        error_sel.cursor = error_cursor
        error_sel.cursor.select(error_cursor.SelectionType.LineUnderCursor)
        extra_selections.append(error_sel)

        # Position for Potential Cause (if not on the first line)
        if line_idx > 0:
            cause_cursor = editor.textCursor()
            cause_cursor.movePosition(cause_cursor.MoveOperation.Start)
            for _ in range(line_idx - 1):
                cause_cursor.movePosition(cause_cursor.MoveOperation.Down)

            cause_sel.cursor = cause_cursor
            cause_sel.cursor.select(cause_cursor.SelectionType.LineUnderCursor)
            extra_selections.append(cause_sel)

        # Apply all selections
        editor.setExtraSelections(extra_selections)

        # Focus on the primary error
        editor.setTextCursor(error_cursor)
        editor.ensureCursorVisible()
        editor.setFocus()

    def load_global_file(self):
        """Load selected global file."""
        path = self.conf_root / self.combo_global_files.currentText()
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self.global_editor.setPlainText(f.read())
                if self.global_hl:
                    self.global_hl.rehighlight()

    def save_global_config(self):
        """Save global config."""
        dest = self.conf_root / self.combo_global_files.currentText()
        self._atomic_save(
            str(dest), self.global_editor.toPlainText(), self.global_editor
        )

    def load_game_file(self, raw_text):
        """Load game-specific override."""
        if not raw_text or "/" in raw_text:
            return
        name = raw_text.split(" (")[0].strip()
        path = self.conf_root / "games.d" / f"{name}.yaml"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self.game_editor.setPlainText(f.read())
        else:
            appid_match = re.search(r"\((\d+)\)", raw_text)
            appid = appid_match.group(1) if appid_match else ""
            if appid:
                hdr = f'# SDY_ID: {appid}\nSTEAM_APPID: "{appid}"\n'
            else:
                hdr = ""
            self.game_editor.setPlainText(
                f'{hdr}# Profile for {name}\nGAME_WRAPPER: ""\n'
                f'GAME_EXTRA_ARGS: ""\nenv_vars:\n  # MANGOHUD: "1"\n'
            )
        if self.game_hl:
            self.game_hl.rehighlight()

    def save_game_profile(self):
        """Save game profile."""
        raw = self.combo_games.currentText().strip()
        if not raw:
            return
        name = raw.split(" (")[0].strip()
        (self.conf_root / "games.d").mkdir(exist_ok=True)
        path = self.conf_root / "games.d" / f"{name}.yaml"
        self._atomic_save(
            str(path), self.game_editor.toPlainText(), self.game_editor
        )

    def refresh_detected_games(self):
        """Scans logs to map games."""
        try:
            home = os.path.expanduser("~")
            parts = [
                "journalctl --since '24 hours ago' --no-hostname",
                f"grep -Ei 'chdir \"{home}|gameID [0-9]|AppID = [0-9]'",
                "grep -vE 'GpuTopology|steamui|/steamapps/common$|bin/'",
                "tail -n 2000",
            ]
            cmd = " | ".join(parts)
            result = subprocess.check_output(cmd, shell=True, text=True)
            self._parse_game_logs(result)
        except (subprocess.SubprocessError, OSError):
            self.combo_games.setPlaceholderText("Journal unavailable.")

    def _parse_game_logs(self, result):
        """Parse log lines into the combo box."""
        detected = {}
        curr = None
        for line in result.splitlines():
            if 'chdir "' in line:
                m = re.search(r'chdir\s+"([^"]+)"', line)
                if m:
                    curr = os.path.basename(m.group(1).rstrip("/"))
                    detected[curr] = curr
            idx = re.search(r"(?:gameID|AppID\s*=\s*)\s*(\d+)", line)
            if idx and curr:
                val = idx.group(1)
                if len(val) > 5:
                    detected[curr] = val

        g_dir = self.conf_root / "games.d"
        if g_dir.exists():
            for f in g_dir.glob("*.yaml"):
                if f.stem not in detected:
                    detected[f.stem] = f.stem

        self.combo_games.clear()
        items = [
            f"{n} ({i})" if i.isdigit() and i != n else n
            for n, i in detected.items()
        ]
        if items:
            self.combo_games.addItems(sorted(items))

    def load_logs(self):
        """Fetch and filter logs with redundancy control."""
        # Reset filter history on every manual or timer-based refresh
        self.log_filter.reset()

        tag = self.tag_filter.currentText()
        # Increased lookback to 12h: shims are rare events
        base = "journalctl --since '12 hours ago' --no-hostname"

        # Noise reduction
        exclusions = (
            "grep -v 'grep' | grep -v 'sdy-control-center' | "
            "grep -v 'drmModeAddFB2WithModifiers failed'"
        )

        if tag == "ALL":
            pattern = (
                r"SELECT:|LAUNCH:|ENGINE:|GAMESCOPE:|SDY:|PROF:|"
                r"STEAM:|BRANCH-SHIM:|\[gamescope\]"
            )
            cmd = f"{base} | grep -Ei '{pattern}' | {exclusions} | tail -n 300"

        elif tag == "GAMESCOPE":
            cmd = (
                f"{base} | grep -Ei 'GAMESCOPE:|\\[gamescope\\]' | "
                f"{exclusions} | tail -n 300"
            )

        elif tag == "STEAM":
            cmd = (
                f"{base} | grep -Ei 'STEAM:|steam\\[' | "
                f"{exclusions} | tail -n 300"
            )

        elif tag == "BRANCH-SHIM":
            # REMOVED the colon requirement for shims to ensure capture
            cmd = (
                f"{base} | grep -Ei 'BRANCH-SHIM' | {exclusions} | tail -n 300"
            )

        else:
            # Standard components still use the colon to avoid false positives
            cmd = f"{base} | grep -Ei '{tag}:' | {exclusions} | tail -n 300"

        try:
            logs = subprocess.check_output(cmd, shell=True, text=True)
            self._display_colored_logs(logs)
        except subprocess.CalledProcessError:
            self.log_display.setPlainText(f"No recent logs found for: {tag}")
        except OSError as err:
            self.log_display.setPlainText(f"OS Error: {err}")

    def _display_colored_logs(self, logs):
        """
        Process logs: filter redundancy, apply icons and colors.
        """
        self.log_display.clear()
        # Note: Order matters. More specific patterns should come first.
        colors = {
            "GAMESCOPE: ARGS": "#3498db",  # Specific Blue for ARGS
            "SELECT": "#f1c40f",
            "LAUNCH": "#2ecc71",
            "ENGINE": "#e67e22",
            "GAMESCOPE": "#ffffff",
            "SDY": "#3498db",
            "PROF": "#1abc9c",
            "STEAM": "#7f8c8d",
            "BRANCH-SHIM": "#e74c3c",
        }

        for line in logs.splitlines():
            if self.log_filter.is_redundant(line):
                continue

            fmt = QTextCharFormat()
            line_upper = line.upper()
            display_text = line

            if any(x in line_upper for x in ["ERROR", "FAILED", "(EE)"]):
                fmt.setForeground(QColor("#c0392b"))
                fmt.setFontWeight(QFont.Weight.Bold)
                display_text = f"❌ {line}"

            elif "SESSION_END_AFTER" in line_upper:
                fmt.setForeground(QColor("#2ecc71"))
                time_info = line.split(":")[-1].strip()
                display_text = f"⏱️ Session metrics: {time_info}"

            else:
                for t_name, t_color in colors.items():
                    is_gs = (
                        t_name == "GAMESCOPE" and "[GAMESCOPE]" in line_upper
                    )
                    if t_name in line_upper or is_gs:
                        fmt.setForeground(QColor(t_color))

                        # Bold for ARGS, Gamescope, or Branch-Shim
                        is_bold_tag = t_name in [
                            "GAMESCOPE: ARGS",
                            "GAMESCOPE",
                            "BRANCH-SHIM",
                        ]
                        if is_bold_tag:
                            fmt.setFontWeight(QFont.Weight.Bold)

                        icons = {"SDY": "🔧", "LAUNCH": "🎮"}
                        icon = icons.get(t_name, "🔹")

                        # Special case: use a different icon for ARGS?
                        # Or keep blue diamond? Let's stay with blue diamond.
                        display_text = f"{icon} {line}"
                        break

            cursor = self.log_display.textCursor()
            cursor.insertText(display_text + "\n", fmt)

        self.log_display.ensureCursorVisible()

    def copy_logs(self):
        """Copy all log content to the system clipboard."""
        log_content = self.log_display.toPlainText()
        if log_content:
            QApplication.clipboard().setText(log_content)
            self.copy_btn.setText("✅ Copied!")
            QTimer.singleShot(2000, lambda: self.copy_btn.setText("📋 Copy"))

    def export_support_log(self):
        """Export log file to disk."""
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save Log", "sdy_support.log"
        )
        if dest:
            with open(dest, "w", encoding="utf-8") as f:
                f.write(self.log_display.toPlainText())

    def _show_completion_message(self, title, message, is_error):
        """Helper to show the final message in the main thread."""
        if is_error:
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def run_backup(self):
        """
        Execute system backup and notify on completion via signals.
        Strictly adhering to English-only documentation and PEP8.
        """
        script = os.path.join(self.lib_path, "backup.py")

        # Immediate user feedback
        QMessageBox.information(
            self, "Backup", "Backup process started in the background..."
        )

        def worker():
            """Background worker for backup execution."""
            try:
                # Run with pkexec for privileges; check=True raises
                # CalledProcessError
                subprocess.run(["pkexec", "python3", script], check=True)

                # Emit success signal to main thread
                self.process_finished.emit(
                    "Success", "System backup completed successfully!", False
                )
            except subprocess.CalledProcessError:
                # Emit error signal if the process fails
                self.process_finished.emit(
                    "Error",
                    "The backup process failed or was cancelled.",
                    True,
                )

        # Start thread as daemon to ensure it doesn't block app closure
        threading.Thread(target=worker, daemon=True).start()

    def run_restore(self):
        """Execute system restore and notify on completion via signals."""

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup Archive", "", "*.tar.gz"
        )
        if not file_path:
            return

        script = os.path.join(self.lib_path, "restore.py")
        QMessageBox.information(
            self,
            "Restore Started",
            "The restore process has started in the background.",
        )

        def worker():
            """Background worker for restore."""
            try:
                subprocess.run(
                    ["pkexec", "python3", script, file_path], check=True
                )
                self.process_finished.emit(
                    "Restore Complete",
                    "System restore finished!\nRestart to apply changes.",
                    False,
                )
            except subprocess.CalledProcessError:
                self.process_finished.emit(
                    "Restore Error", "The restore process failed.", True
                )

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SDYControlCenter()
    window.show()
    sys.exit(app.exec())
