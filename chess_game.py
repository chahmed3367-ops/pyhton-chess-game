import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import random
import sys

import chess
import chess.pgn


SQUARE_SIZE = 70
BOARD_SIZE = SQUARE_SIZE * 8
MARGIN = 22
CANVAS_SIZE = BOARD_SIZE + MARGIN * 2

COLORS = {
    "background": "#17202b",
    "panel": "#202b38",
    "light": "#eee6d5",
    "dark": "#75936d",
    "selected": "#f6d365",
    "last_move": "#c9d675",
    "legal": "#4c7c59",
    "white_piece": "#fffdf7",
    "black_piece": "#20252c",
    "text": "#f4f6f8",
    "muted": "#bdc6cf",
    "accent": "#d7ae62",
    "danger": "#df6b67",
    "ivory_top": "#fff9e9",
    "ivory_mid": "#e8d9b5",
    "ivory_edge": "#a78c60",
    "ivory_shadow": "#7d694d",
    "ebony_top": "#626e79",
    "ebony_mid": "#303b47",
    "ebony_edge": "#17202b",
    "ebony_shadow": "#10151c",
    "shine": "#ffffff",
}

BOARD_THEMES = {
    "Classic": ("#eee6d5", "#75936d"),
    "Wood": ("#f0d2a2", "#9b613c"),
    "Emerald": ("#e5eadf", "#4f8068"),
    "Midnight": ("#aeb9c9", "#42536d"),
}


class ChessGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Chess · Python")
        self.root.configure(bg=COLORS["background"])
        self.root.resizable(False, False)

        self.board = chess.Board()
        self.selected = None
        self.legal_targets = []
        self.animating = False
        self.animation_job = None
        self.animation = None
        self.last_move = None
        self.rotated = False
        self.captured_white = []
        self.captured_black = []
        self.ai_enabled = tk.BooleanVar(value=False)
        self.ai_color = chess.BLACK
        self.ai_side = tk.StringVar(value="Black")
        self.ai_difficulty = tk.StringVar(value="Normal")
        self.sound_enabled = tk.BooleanVar(value=True)
        self.result_shown = False
        self.ai_job = None
        self.board_theme = tk.StringVar(value="Classic")
        self.settings_window = None

        self.build_ui()
        self.draw_board()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def build_ui(self):
        header = tk.Frame(self.root, bg=COLORS["background"])
        header.pack(fill="x", padx=24, pady=(18, 8))

        tk.Label(
            header, text="CHESS", bg=COLORS["background"],
            fg=COLORS["text"], font=("Segoe UI", 20, "bold")
        ).pack(side="left")
        tk.Label(
            header, text="A classic match", bg=COLORS["background"],
            fg=COLORS["muted"], font=("Segoe UI", 10)
        ).pack(side="left", padx=(12, 0), pady=(7, 0))

        game_area = tk.Frame(self.root, bg=COLORS["background"])
        game_area.pack(padx=10)

        self.white_capture_panel = self.make_capture_panel(game_area, "WHITE CAPTURED")
        self.canvas = tk.Canvas(
            game_area, width=CANVAS_SIZE, height=CANVAS_SIZE,
            bg=COLORS["background"], highlightthickness=0
        )
        self.canvas.pack(side="left")
        self.black_capture_panel = self.make_capture_panel(game_area, "BLACK CAPTURED")
        self.history_panel = self.make_history_panel(game_area)
        self.canvas.bind("<Button-1>", self.on_click)

        footer = tk.Frame(self.root, bg=COLORS["panel"])
        footer.pack(fill="x", padx=24, pady=(8, 20))

        info = tk.Frame(footer, bg=COLORS["panel"])
        info.pack(side="left", fill="both", expand=True, padx=14, pady=10)
        self.status = tk.Label(
            info, text="White to move", bg=COLORS["panel"],
            fg=COLORS["text"], font=("Segoe UI", 13, "bold"), anchor="w"
        )
        self.status.pack(anchor="w")
        self.detail = tk.Label(
            info, text="Select a piece to see its legal moves",
            bg=COLORS["panel"], fg=COLORS["muted"],
            font=("Segoe UI", 9), anchor="w"
        )
        self.detail.pack(anchor="w", pady=(3, 0))

        buttons = tk.Frame(footer, bg=COLORS["panel"])
        buttons.pack(side="right", padx=12, pady=12)
        self.make_button(buttons, "Rotate view", self.rotate_view).pack(
            side="left", padx=4
        )
        self.make_button(buttons, "Save PGN", self.save_pgn).pack(side="left", padx=4)
        self.make_button(buttons, "Load PGN", self.load_pgn).pack(side="left", padx=4)
        self.make_button(buttons, "Undo", self.undo).pack(side="left", padx=4)
        self.make_button(buttons, "New game", self.restart, accent=True).pack(
            side="left", padx=4
        )

        settings = tk.Frame(self.root, bg=COLORS["background"])
        settings.pack(fill="x", padx=28, pady=(0, 10))
        self.make_button(settings, "Settings", self.open_settings).pack(side="right")

    def open_settings(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.title("Chess settings")
        window.configure(bg=COLORS["background"])
        window.resizable(False, False)
        window.transient(self.root)
        window.grab_set()

        tk.Label(window, text="Settings", bg=COLORS["background"],
                 fg=COLORS["text"], font=("Segoe UI", 18, "bold")).pack(
                     anchor="w", padx=22, pady=(18, 12))
        options = tk.Frame(window, bg=COLORS["panel"])
        options.pack(fill="both", padx=16, pady=(0, 16))

        tk.Checkbutton(
            options, text="Play against computer", variable=self.ai_enabled,
            command=self.on_settings_changed, bg=COLORS["panel"], fg=COLORS["text"],
            activebackground=COLORS["panel"], activeforeground=COLORS["text"],
            selectcolor="#344354", font=("Segoe UI", 10)
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 8))
        self.add_setting_picker(options, "Computer plays", self.ai_side,
                                ("Black", "White"), 1, self.on_settings_changed)
        self.add_setting_picker(options, "Difficulty", self.ai_difficulty,
                                ("Easy", "Normal", "Hard"), 2)
        self.add_setting_picker(options, "Board theme", self.board_theme,
                                tuple(BOARD_THEMES), 3, self.apply_theme)
        tk.Checkbutton(
            options, text="Enable sound effects", variable=self.sound_enabled,
            bg=COLORS["panel"], fg=COLORS["text"], activebackground=COLORS["panel"],
            activeforeground=COLORS["text"], selectcolor="#344354",
            font=("Segoe UI", 10)
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 16))
        self.make_button(window, "Done", window.destroy, accent=True).pack(
            anchor="e", padx=18, pady=(0, 16))

    def add_setting_picker(self, parent, label, variable, choices, row, callback=None):
        tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["muted"],
                 font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w",
                                              padx=16, pady=8)
        picker = tk.OptionMenu(parent, variable, *choices,
                               command=(lambda _value: callback()) if callback else None)
        picker.config(bg="#344354", fg=COLORS["text"], relief="flat",
                      highlightthickness=0, font=("Segoe UI", 9), width=12)
        picker["menu"].config(bg="#344354", fg=COLORS["text"])
        picker.grid(row=row, column=1, sticky="e", padx=16, pady=8)

    def apply_theme(self):
        COLORS["light"], COLORS["dark"] = BOARD_THEMES[self.board_theme.get()]
        self.draw_board()

    def save_pgn(self):
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Save chess game", defaultextension=".pgn",
            filetypes=(("PGN chess game", "*.pgn"), ("All files", "*.*"))
        )
        if not path:
            return
        game = chess.pgn.Game.from_board(self.board)
        game.headers["Event"] = "Python Chess Game"
        game.headers["White"] = "White"
        game.headers["Black"] = "Computer" if self.ai_enabled.get() else "Black"
        game.headers["Result"] = self.board.result(claim_draw=True)
        try:
            with open(path, "w", encoding="utf-8") as pgn_file:
                print(game, file=pgn_file, end="\n\n")
        except OSError as error:
            messagebox.showerror("Could not save PGN", str(error), parent=self.root)

    def load_pgn(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="Load chess game",
            filetypes=(("PGN chess game", "*.pgn"), ("All files", "*.*"))
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as pgn_file:
                game = chess.pgn.read_game(pgn_file)
        except (OSError, UnicodeError) as error:
            messagebox.showerror("Could not load PGN", str(error), parent=self.root)
            return
        if game is None:
            messagebox.showerror("Invalid PGN", "No chess game was found in this file.",
                                 parent=self.root)
            return

        self.cancel_animation()
        if self.ai_job is not None:
            self.root.after_cancel(self.ai_job)
            self.ai_job = None
        for window in self.root.winfo_children():
            if isinstance(window, tk.Toplevel):
                window.destroy()
        self.board = game.end().board()
        self.last_move = self.board.peek() if self.board.move_stack else None
        self.selected = None
        self.legal_targets = []
        self.result_shown = False
        self.rebuild_captures()
        self.draw_board()
        self.maybe_make_ai_move()

    def make_capture_panel(self, parent, title):
        panel = tk.Frame(parent, bg=COLORS["panel"], width=110, height=CANVAS_SIZE)
        panel.pack(side="left", padx=5, fill="y")
        panel.pack_propagate(False)
        tk.Label(
            panel, text=title, bg=COLORS["panel"], fg=COLORS["muted"],
            font=("Segoe UI", 8, "bold"), wraplength=95
        ).pack(pady=(12, 8))
        pieces = tk.Label(
            panel, text="", bg=COLORS["panel"], fg=COLORS["text"],
            font=("Segoe UI Symbol", 24), justify="center", wraplength=92
        )
        pieces.pack(padx=6, pady=4, fill="x")
        return pieces

    def make_history_panel(self, parent):
        panel = tk.Frame(parent, bg=COLORS["panel"], width=160, height=CANVAS_SIZE)
        panel.pack(side="left", padx=5, fill="y")
        panel.pack_propagate(False)
        tk.Label(panel, text="MOVE HISTORY", bg=COLORS["panel"],
                 fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).pack(pady=(12, 8))
        self.history = tk.Listbox(
            panel, bg=COLORS["panel"], fg=COLORS["text"],
            selectbackground="#344354", borderwidth=0, highlightthickness=0,
            font=("Consolas", 9), activestyle="none"
        )
        self.history.pack(fill="both", expand=True, padx=8, pady=(0, 10))
        return self.history

    def update_history(self):
        self.history.delete(0, tk.END)
        sans = []
        replay = self.board.root()
        for move in self.board.move_stack:
            sans.append(replay.san(move))
            replay.push(move)
        for index in range(0, len(sans), 2):
            white = sans[index]
            black = sans[index + 1] if index + 1 < len(sans) else ""
            self.history.insert(tk.END, f"{index // 2 + 1:>2}. {white:<7} {black}")
        if self.history.size():
            self.history.see(tk.END)

    def on_settings_changed(self):
        self.ai_color = chess.WHITE if self.ai_side.get() == "White" else chess.BLACK
        if self.ai_job is not None:
            self.root.after_cancel(self.ai_job)
            self.ai_job = None
        self.maybe_make_ai_move()

    def play_sound(self, kind="move"):
        if not self.sound_enabled.get():
            return
        try:
            if sys.platform == "win32":
                import winsound
                winsound.MessageBeep(
                    winsound.MB_ICONEXCLAMATION if kind == "capture" else winsound.MB_OK
                )
            else:
                self.root.bell()
        except Exception:
            pass

    def update_captures(self):
        symbols = {
            chess.PAWN: "♟", chess.KNIGHT: "♞", chess.BISHOP: "♝",
            chess.ROOK: "♜", chess.QUEEN: "♛",
        }
        self.white_capture_panel.config(
            text="\n".join(symbols[piece.piece_type] for piece in self.captured_white)
            or "—"
        )
        self.black_capture_panel.config(
            text="\n".join(symbols[piece.piece_type] for piece in self.captured_black)
            or "—"
        )

    def make_button(self, parent, label, command, accent=False):
        return tk.Button(
            parent, text=label, command=command,
            bg=COLORS["accent"] if accent else "#344354",
            fg="#17202b" if accent else COLORS["text"],
            activebackground="#e4bf76" if accent else "#43566b",
            activeforeground="#17202b" if accent else COLORS["text"],
            relief="flat", borderwidth=0, padx=13, pady=8,
            font=("Segoe UI", 9, "bold"), cursor="hand2"
        )

    def square_center(self, square):
        col, row = self.square_to_view(square)
        return (MARGIN + col * SQUARE_SIZE + SQUARE_SIZE / 2,
                MARGIN + row * SQUARE_SIZE + SQUARE_SIZE / 2)

    def square_to_view(self, square):
        file_index = chess.square_file(square)
        rank_index = chess.square_rank(square)
        if self.rotated:
            return 7 - file_index, rank_index
        return file_index, 7 - rank_index

    def view_to_square(self, col, row):
        if self.rotated:
            return chess.square(7 - col, row)
        return chess.square(col, 7 - row)

    def draw_board(self, moving_piece=None):
        self.canvas.delete("all")

        for row in range(8):
            for col in range(8):
                square = self.view_to_square(col, row)
                x1 = MARGIN + col * SQUARE_SIZE
                y1 = MARGIN + row * SQUARE_SIZE
                x2, y2 = x1 + SQUARE_SIZE, y1 + SQUARE_SIZE

                color = COLORS["light"] if (row + col) % 2 == 0 else COLORS["dark"]
                if self.last_move and square in (self.last_move.from_square,
                                                  self.last_move.to_square):
                    color = COLORS["last_move"]
                if square == self.selected:
                    color = COLORS["selected"]

                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=color, outline=color
                )

                # Mark the king in check with a soft red square.
                piece = self.board.piece_at(square)
                if piece and piece.piece_type == chess.KING and piece.color == self.board.turn:
                    if self.board.is_check():
                        self.canvas.create_rectangle(
                            x1, y1, x2, y2, fill=COLORS["danger"],
                            stipple="gray50", outline=""
                        )

                if square in self.legal_targets:
                    cx, cy = self.square_center(square)
                    if piece:
                        self.canvas.create_oval(
                            x1 + 5, y1 + 5, x2 - 5, y2 - 5,
                            outline=COLORS["legal"], width=5
                        )
                    else:
                        self.canvas.create_oval(
                            cx - 8, cy - 8, cx + 8, cy + 8,
                            fill=COLORS["legal"], outline=""
                        )

                if piece and square != moving_piece:
                    self.draw_piece(square, piece)

        # Coordinate labels sit just outside the board.
        files = "hgfedcba" if self.rotated else "abcdefgh"
        ranks = "12345678" if self.rotated else "87654321"
        for col, file_name in enumerate(files):
            x = MARGIN + col * SQUARE_SIZE + SQUARE_SIZE - 8
            self.canvas.create_text(
                x, MARGIN + BOARD_SIZE + 11, text=file_name,
                fill=COLORS["muted"], font=("Segoe UI", 9, "bold")
            )
        for row in range(8):
            rank_name = ranks[row]
            y = MARGIN + row * SQUARE_SIZE + 9
            self.canvas.create_text(
                10, y, text=rank_name, fill=COLORS["muted"],
                font=("Segoe UI", 9, "bold")
            )

        self.update_status()
        self.update_captures()
        self.update_history()
        self.show_result_if_over()

    def draw_piece(self, square, piece, x=None, y=None):
        if x is None or y is None:
            x, y = self.square_center(square)
        palette = "ivory" if piece.color else "ebony"
        self.draw_piece_shadow(x, y)

        # Each piece is drawn from overlapping, outlined shapes. The layered
        # highlights and dark lower edges create a sculpted, 3D-style look.
        self.draw_piece_base(x, y, palette)
        kind = piece.piece_type
        if kind == chess.PAWN:
            self.draw_pawn(x, y, palette)
        elif kind == chess.ROOK:
            self.draw_rook(x, y, palette)
        elif kind == chess.KNIGHT:
            self.draw_knight(x, y, palette)
        elif kind == chess.BISHOP:
            self.draw_bishop(x, y, palette)
        elif kind == chess.QUEEN:
            self.draw_queen(x, y, palette)
        elif kind == chess.KING:
            self.draw_king(x, y, palette)

    def create_polygon(self, points, fill, outline, width=1):
        self.canvas.create_polygon(
            *points, fill=fill, outline=outline, width=width,
            joinstyle=tk.ROUND, tags="piece"
        )

    def create_oval(self, x1, y1, x2, y2, fill, outline, width=1):
        self.canvas.create_oval(
            x1, y1, x2, y2, fill=fill, outline=outline, width=width,
            tags="piece"
        )

    def create_rect(self, x1, y1, x2, y2, fill, outline, width=1):
        self.canvas.create_rectangle(
            x1, y1, x2, y2, fill=fill, outline=outline, width=width,
            tags="piece"
        )

    def draw_piece_shadow(self, x, y):
        self.create_oval(x - 21, y + 24, x + 22, y + 31,
                         "#17202b", "#17202b")

    def draw_piece_base(self, x, y, palette):
        edge = COLORS[f"{palette}_edge"]
        mid = COLORS[f"{palette}_mid"]
        shadow = COLORS[f"{palette}_shadow"]
        top = COLORS[f"{palette}_top"]
        self.create_oval(x - 23, y + 17, x + 23, y + 29, shadow, edge, 1)
        self.create_oval(x - 21, y + 14, x + 21, y + 25, mid, edge, 1)
        self.create_oval(x - 17, y + 15, x - 2, y + 18, top, top, 0)
        self.create_oval(x - 16, y + 20, x + 16, y + 24, shadow, shadow, 0)

    def draw_stem(self, x, y, palette, half_width, top_y, bottom_y):
        edge = COLORS[f"{palette}_edge"]
        mid = COLORS[f"{palette}_mid"]
        top = COLORS[f"{palette}_top"]
        self.create_polygon(
            [(x - half_width, bottom_y), (x - half_width + 3, top_y),
             (x + half_width - 3, top_y), (x + half_width, bottom_y)],
            mid, edge, 1
        )
        self.create_polygon(
            [(x - half_width + 2, bottom_y - 2),
             (x - half_width + 5, top_y + 2), (x - 2, top_y + 2),
             (x - 3, bottom_y - 2)], top, top, 0
        )

    def draw_pawn(self, x, y, palette):
        edge = COLORS[f"{palette}_edge"]
        mid = COLORS[f"{palette}_mid"]
        top = COLORS[f"{palette}_top"]
        self.draw_stem(x, y, palette, 9, y + 1, y + 17)
        self.create_oval(x - 14, y - 3, x + 14, y + 7, mid, edge, 1)
        self.create_oval(x - 10, y - 19, x + 10, y + 2, mid, edge, 1)
        self.create_oval(x - 8, y - 18, x - 1, y - 12, top, top, 0)

    def draw_rook(self, x, y, palette):
        edge = COLORS[f"{palette}_edge"]
        mid = COLORS[f"{palette}_mid"]
        top = COLORS[f"{palette}_top"]
        self.draw_stem(x, y, palette, 12, y - 8, y + 17)
        self.create_oval(x - 15, y - 13, x + 15, y - 6, mid, edge, 1)
        self.create_rect(x - 17, y - 25, x + 17, y - 13, mid, edge, 1)
        self.create_rect(x - 19, y - 29, x + 19, y - 23, mid, edge, 1)
        for dx in (-14, -5, 5, 14):
            self.create_rect(x + dx - 3, y - 34, x + dx + 3, y - 26,
                             mid, edge, 1)
        self.create_rect(x - 15, y - 28, x - 10, y - 24, top, top, 0)

    def draw_bishop(self, x, y, palette):
        edge = COLORS[f"{palette}_edge"]
        mid = COLORS[f"{palette}_mid"]
        top = COLORS[f"{palette}_top"]
        self.draw_stem(x, y, palette, 10, y + 1, y + 17)
        self.create_oval(x - 13, y - 4, x + 13, y + 5, mid, edge, 1)
        self.create_polygon(
            [(x, y - 34), (x + 11, y - 16), (x + 9, y - 4),
             (x - 9, y - 4), (x - 11, y - 16)], mid, edge, 1
        )
        self.create_polygon(
            [(x - 7, y - 15), (x - 1, y - 26), (x + 1, y - 16),
             (x - 2, y - 4), (x - 8, y - 4)], top, top, 0
        )
        self.create_oval(x - 3, y - 34, x + 3, y - 28, top, edge, 1)

    def draw_queen(self, x, y, palette):
        edge = COLORS[f"{palette}_edge"]
        mid = COLORS[f"{palette}_mid"]
        top = COLORS[f"{palette}_top"]
        self.draw_stem(x, y, palette, 12, y - 7, y + 17)
        self.create_oval(x - 17, y - 12, x + 17, y - 4, mid, edge, 1)
        self.create_polygon(
            [(x - 17, y - 13), (x - 14, y - 29), (x - 5, y - 19),
             (x, y - 34), (x + 6, y - 19), (x + 15, y - 29),
             (x + 18, y - 13)], mid, edge, 1
        )
        self.create_polygon(
            [(x - 12, y - 15), (x - 10, y - 26), (x - 4, y - 18),
             (x - 1, y - 30), (x + 2, y - 17), (x + 8, y - 25),
             (x + 12, y - 15)], top, top, 0
        )
        for dx, dy in ((-14, -32), (0, -38), (14, -32)):
            self.create_oval(x + dx - 3, y + dy - 3, x + dx + 3,
                             y + dy + 3, top, edge, 1)

    def draw_king(self, x, y, palette):
        edge = COLORS[f"{palette}_edge"]
        mid = COLORS[f"{palette}_mid"]
        top = COLORS[f"{palette}_top"]
        self.draw_stem(x, y, palette, 13, y - 7, y + 17)
        self.create_oval(x - 17, y - 12, x + 17, y - 4, mid, edge, 1)
        self.create_polygon(
            [(x - 14, y - 13), (x - 11, y - 26),
             (x + 11, y - 26), (x + 14, y - 13)], mid, edge, 1
        )
        self.create_rect(x - 3, y - 43, x + 3, y - 24, top, edge, 1)
        self.create_rect(x - 10, y - 37, x + 10, y - 31, top, edge, 1)
        self.create_rect(x - 1, y - 41, x + 1, y - 26,
                         COLORS["shine"], COLORS["shine"], 0)

    def draw_knight(self, x, y, palette):
        edge = COLORS[f"{palette}_edge"]
        mid = COLORS[f"{palette}_mid"]
        top = COLORS[f"{palette}_top"]
        self.draw_stem(x, y, palette, 11, y + 1, y + 17)
        self.create_polygon(
            [(x - 13, y + 1), (x - 14, y - 13), (x - 6, y - 22),
             (x - 11, y - 34), (x + 1, y - 29), (x + 13, y - 17),
             (x + 12, y - 4), (x + 4, y + 2)], mid, edge, 1
        )
        self.create_polygon(
            [(x - 8, y - 4), (x - 9, y - 14), (x - 3, y - 24),
             (x + 5, y - 17), (x + 9, y - 8), (x + 2, y - 3)],
            top, top, 0
        )
        self.create_oval(x + 2, y - 20, x + 5, y - 17,
                         edge, edge, 0)


    def update_status(self):
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn else "White"
            text, detail = f"{winner} wins by checkmate", "Game over · restart to play again"
        elif self.board.is_stalemate():
            text, detail = "Draw by stalemate", "Game over · restart to play again"
        elif self.board.is_insufficient_material():
            text, detail = "Draw · insufficient material", "Game over · restart to play again"
        elif self.board.is_check():
            text = ("White" if self.board.turn else "Black") + " is in check"
            detail = "Find a safe move for your king"
        else:
            text = ("White" if self.board.turn else "Black") + " to move"
            detail = "Select a piece to see its legal moves"
        self.status.config(text=text)
        self.detail.config(text=detail)

    def show_result_if_over(self):
        if not self.board.is_game_over() or self.result_shown:
            return
        self.result_shown = True
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            subtitle = "CHECKMATE"
            title = f"{winner} wins!"
        elif self.board.is_stalemate():
            subtitle, title = "STALEMATE", "It's a draw"
        else:
            subtitle, title = self.board.result(), "It's a draw"
        overlay = tk.Toplevel(self.root)
        overlay.title("Game finished")
        overlay.configure(bg=COLORS["panel"])
        overlay.resizable(False, False)
        overlay.transient(self.root)
        overlay.grab_set()
        tk.Label(overlay, text=subtitle, bg=COLORS["panel"], fg=COLORS["accent"],
                 font=("Segoe UI", 10, "bold")).pack(padx=36, pady=(24, 5))
        tk.Label(overlay, text=title, bg=COLORS["panel"], fg=COLORS["text"],
                 font=("Segoe UI", 24, "bold")).pack(padx=36, pady=5)
        tk.Label(overlay, text="Start a new game to play again.",
                 bg=COLORS["panel"], fg=COLORS["muted"],
                 font=("Segoe UI", 10)).pack(pady=(2, 16))
        self.make_button(overlay, "New game", lambda: (overlay.destroy(), self.restart()),
                         accent=True).pack(pady=(0, 22))
        overlay.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - overlay.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - overlay.winfo_height()) // 2
        overlay.geometry(f"+{x}+{y}")

    def on_click(self, event):
        if self.animating or self.board.is_game_over():
            return
        if self.ai_enabled.get() and self.board.turn == self.ai_color:
            return
        col = (event.x - MARGIN) // SQUARE_SIZE
        row = (event.y - MARGIN) // SQUARE_SIZE
        if not (0 <= row < 8 and 0 <= col < 8):
            return

        square = self.view_to_square(col, row)
        piece = self.board.piece_at(square)
        if self.selected is None:
            if piece and piece.color == self.board.turn:
                self.select_piece(square)
            return

        if square == self.selected:
            self.selected = None
            self.legal_targets = []
            self.draw_board()
            return

        move = self.find_move(self.selected, square)
        if move is not None:
            self.make_move(move)
        elif piece and piece.color == self.board.turn:
            self.select_piece(square)
        else:
            self.selected = None
            self.legal_targets = []
            self.draw_board()

    def find_move(self, from_square, to_square):
        piece = self.board.piece_at(from_square)
        if piece and piece.piece_type == chess.PAWN:
            if chess.square_rank(to_square) in (0, 7):
                choice = simpledialog.askstring(
                    "Pawn promotion",
                    "Promote to: Queen, Rook, Bishop or Knight?",
                    initialvalue="Queen", parent=self.root
                )
                options = {
                    "queen": chess.QUEEN, "rook": chess.ROOK,
                    "bishop": chess.BISHOP, "knight": chess.KNIGHT,
                }
                if choice is None:
                    return None
                promotion = options.get(choice.strip().lower())
                if promotion is None:
                    messagebox.showwarning(
                        "Invalid choice",
                        "Please enter Queen, Rook, Bishop or Knight.",
                        parent=self.root
                    )
                    return None
                candidate = chess.Move(from_square, to_square, promotion=promotion)
                return candidate if candidate in self.board.legal_moves else None

        candidate = chess.Move(from_square, to_square)
        return candidate if candidate in self.board.legal_moves else None

    def select_piece(self, square):
        self.selected = square
        self.legal_targets = [
            move.to_square for move in self.board.legal_moves
            if move.from_square == square
        ]
        self.draw_board()

    def make_move(self, move):
        moving_piece = self.board.piece_at(move.from_square)
        captured_piece = self.board.piece_at(move.to_square)
        if self.board.is_en_passant(move):
            captured_piece = self.board.piece_at(
                move.to_square - 8 if self.board.turn == chess.WHITE
                else move.to_square + 8
            )
        self.board.push(move)
        if captured_piece:
            # A captured white piece is shown in Black's tray and vice versa.
            tray = self.captured_black if captured_piece.color else self.captured_white
            tray.append(captured_piece)
        self.last_move = move
        self.play_sound("capture" if captured_piece else "move")
        self.selected = None
        self.legal_targets = []

        # Draw the new position, then animate the moved piece over it.
        self.draw_board(moving_piece=move.to_square)
        self.animating = True
        start = self.square_center(move.from_square)
        end = self.square_center(move.to_square)
        self.animation = {
            "piece": self.board.piece_at(move.to_square),
            "to_square": move.to_square,
            "start": start,
            "end": end,
            "step": 0,
            "steps": 12,
        }
        self.animate_step()

    def animate_step(self):
        if not self.animation:
            self.animating = False
            return
        animation = self.animation
        animation["step"] += 1
        progress = animation["step"] / animation["steps"]
        # Smooth ease-in/ease-out interpolation.
        eased = progress * progress * (3 - 2 * progress)
        sx, sy = animation["start"]
        ex, ey = animation["end"]
        x = sx + (ex - sx) * eased
        y = sy + (ey - sy) * eased

        self.draw_board(moving_piece=animation["to_square"])
        self.draw_piece(animation["to_square"], animation["piece"], x, y)

        if animation["step"] >= animation["steps"]:
            self.animation = None
            self.animating = False
            self.draw_board()
            self.maybe_make_ai_move()
        else:
            self.animation_job = self.root.after(16, self.animate_step)

    def undo(self):
        self.cancel_animation()
        if self.board.move_stack:
            self.board.pop()
            if self.ai_enabled.get() and self.board.move_stack and self.board.turn == self.ai_color:
                self.board.pop()
            self.rebuild_captures()
            self.last_move = self.board.peek() if self.board.move_stack else None
            self.result_shown = False
            for window in self.root.winfo_children():
                if isinstance(window, tk.Toplevel):
                    window.destroy()
            self.selected = None
            self.legal_targets = []
            self.draw_board()

    def restart(self):
        self.cancel_animation()
        if self.ai_job is not None:
            self.root.after_cancel(self.ai_job)
            self.ai_job = None
        self.board.reset()
        self.selected = None
        self.legal_targets = []
        self.last_move = None
        self.captured_white = []
        self.captured_black = []
        self.result_shown = False
        for window in self.root.winfo_children():
            if isinstance(window, tk.Toplevel):
                window.destroy()
        self.draw_board()
        self.maybe_make_ai_move()

    def maybe_make_ai_move(self):
        if (self.ai_enabled.get() and self.board.turn == self.ai_color
                and not self.board.is_game_over() and not self.animating
                and self.ai_job is None):
            self.status.config(text="Computer is thinking…")
            self.ai_job = self.root.after(250, self.make_ai_move)

    def make_ai_move(self):
        self.ai_job = None
        if (not self.ai_enabled.get() or self.board.turn != self.ai_color
                or self.board.is_game_over()):
            return
        depth = {"Easy": 1, "Normal": 2, "Hard": 3}.get(self.ai_difficulty.get(), 2)
        move = self.choose_ai_move(depth)
        if move:
            self.make_move(move)

    def choose_ai_move(self, depth):
        moves = list(self.board.legal_moves)
        if not moves:
            return None
        random.shuffle(moves)
        moves.sort(key=self.move_order_score, reverse=True)
        maximizing = self.board.turn == chess.WHITE
        best_move = moves[0]
        best_score = float("-inf") if maximizing else float("inf")
        alpha, beta = float("-inf"), float("inf")
        for move in moves:
            self.board.push(move)
            score = self.search_position(depth - 1, alpha, beta)
            self.board.pop()
            if ((maximizing and score > best_score)
                    or (not maximizing and score < best_score)):
                best_score, best_move = score, move
            if maximizing:
                alpha = max(alpha, best_score)
            else:
                beta = min(beta, best_score)
        return best_move

    def search_position(self, depth, alpha, beta):
        if self.board.is_game_over():
            return self.evaluate_board()
        if depth <= 0:
            return self.quiescence(alpha, beta, 0)
        maximizing = self.board.turn == chess.WHITE
        best = float("-inf") if maximizing else float("inf")
        moves = list(self.board.legal_moves)
        random.shuffle(moves)
        moves.sort(key=self.move_order_score, reverse=True)
        for move in moves:
            self.board.push(move)
            score = self.search_position(depth - 1, alpha, beta)
            self.board.pop()
            if maximizing:
                best = max(best, score)
                alpha = max(alpha, best)
            else:
                best = min(best, score)
                beta = min(beta, best)
            if beta <= alpha:
                break
        return best

    def move_order_score(self, move):
        moving = self.board.piece_at(move.from_square)
        captured = self.board.piece_at(move.to_square)
        if self.board.is_en_passant(move):
            captured = chess.Piece(chess.PAWN, not self.board.turn)
        values = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
                  chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000}
        score = 0
        if captured:
            score += 10 * values[captured.piece_type] - values[moving.piece_type]
        if move.promotion:
            score += values[move.promotion]
        return score

    def quiescence(self, alpha, beta, ply):
        if self.board.is_game_over():
            return self.evaluate_board()
        if ply >= 6:
            return self.evaluate_board()
        maximizing = self.board.turn == chess.WHITE
        in_check = self.board.is_check()
        stand_pat = self.evaluate_board()
        if not in_check:
            if maximizing:
                if stand_pat >= beta:
                    return beta
                alpha = max(alpha, stand_pat)
            else:
                if stand_pat <= alpha:
                    return alpha
                beta = min(beta, stand_pat)

        moves = [move for move in self.board.legal_moves
                 if in_check or self.board.is_capture(move) or move.promotion]
        moves.sort(key=self.move_order_score, reverse=True)
        best = float("-inf") if maximizing else float("inf")
        if not moves and in_check:
            return stand_pat
        for move in moves:
            self.board.push(move)
            score = self.quiescence(alpha, beta, ply + 1)
            self.board.pop()
            if maximizing:
                best = max(best, score)
                alpha = max(alpha, best)
            else:
                best = min(best, score)
                beta = min(beta, best)
            if beta <= alpha:
                break
        if not moves:
            return stand_pat
        return best

    def evaluate_board(self):
        if self.board.is_checkmate():
            return -100000 if self.board.turn == chess.WHITE else 100000
        if self.board.is_game_over():
            return 0
        values = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 335,
                  chess.ROOK: 510, chess.QUEEN: 950, chess.KING: 0}
        score = 0
        non_pawn_material = sum(
            len(self.board.pieces(piece_type, color)) * value
            for piece_type, value in values.items()
            if piece_type not in (chess.PAWN, chess.KING)
            for color in (chess.WHITE, chess.BLACK)
        )
        endgame = non_pawn_material < 2600

        for color in (chess.WHITE, chess.BLACK):
            sign = 1 if color == chess.WHITE else -1
            pawns_by_file = [0] * 8
            bishops = 0
            for square, piece in self.board.piece_map().items():
                if piece.color != color:
                    continue
                piece_type = piece.piece_type
                file_index = chess.square_file(square)
                rank = chess.square_rank(square)
                relative_rank = rank if color == chess.WHITE else 7 - rank
                center = 7 - (abs(2 * file_index - 7) + abs(2 * rank - 7))
                score += sign * values[piece_type]

                if piece_type == chess.PAWN:
                    pawns_by_file[file_index] += 1
                    score += sign * relative_rank * 9
                    if relative_rank >= 4:
                        score += sign * center * 2
                    if self.is_passed_pawn(square, color):
                        score += sign * (relative_rank ** 2) * 4
                elif piece_type in (chess.KNIGHT, chess.BISHOP):
                    score += sign * center * (5 if piece_type == chess.KNIGHT else 3)
                    if piece_type == chess.BISHOP:
                        bishops += 1
                elif piece_type == chess.ROOK:
                    if relative_rank == 6:
                        score += sign * 22
                    file_has_pawn = any(
                        chess.square_file(pawn_square) == file_index
                        for color in (chess.WHITE, chess.BLACK)
                        for pawn_square in self.board.pieces(chess.PAWN, color)
                    )
                    if not file_has_pawn:
                        score += sign * 12
                elif piece_type == chess.QUEEN:
                    score += sign * center
                elif piece_type == chess.KING:
                    if endgame:
                        score += sign * center * 5
                    else:
                        score += sign * (8 - center) * 2
                        # Reward friendly pawns sheltering the king.
                        forward = 1 if color == chess.WHITE else -1
                        for df in (-1, 0, 1):
                            f, r = file_index + df, rank + forward
                            if 0 <= f < 8 and 0 <= r < 8:
                                shelter = self.board.piece_at(chess.square(f, r))
                                if shelter == chess.Piece(chess.PAWN, color):
                                    score += sign * 12

            # Doubled and isolated pawns are structural weaknesses.
            for file_index, count in enumerate(pawns_by_file):
                if count > 1:
                    score -= sign * (count - 1) * 14
                if count and not any(
                    pawns_by_file[adjacent]
                    for adjacent in (file_index - 1, file_index + 1)
                    if 0 <= adjacent < 8
                ):
                    score -= sign * count * 12
            if bishops >= 2:
                score += sign * 28

        # Small mobility and check bonuses help the AI choose active moves.
        current_mobility = sum(1 for _ in self.board.legal_moves)
        score += current_mobility * (2 if self.board.turn == chess.WHITE else -2)
        if self.board.is_check():
            score += -24 if self.board.turn == chess.WHITE else 24
        return score

    def is_passed_pawn(self, square, color):
        file_index = chess.square_file(square)
        rank = chess.square_rank(square)
        enemy_pawns = self.board.pieces(chess.PAWN, not color)
        for enemy_square in enemy_pawns:
            enemy_file = chess.square_file(enemy_square)
            enemy_rank = chess.square_rank(enemy_square)
            if abs(enemy_file - file_index) > 1:
                continue
            if color == chess.WHITE and enemy_rank > rank:
                return False
            if color == chess.BLACK and enemy_rank < rank:
                return False
        return True

    def rebuild_captures(self):
        self.captured_white = []
        self.captured_black = []
        replay = self.board.root()
        for move in self.board.move_stack:
            captured_piece = replay.piece_at(move.to_square)
            if replay.is_en_passant(move):
                captured_piece = replay.piece_at(
                    move.to_square - 8 if replay.turn == chess.WHITE
                    else move.to_square + 8
                )
            if captured_piece:
                tray = self.captured_black if captured_piece.color else self.captured_white
                tray.append(captured_piece)
            replay.push(move)

    def rotate_view(self):
        if self.animating:
            return
        self.rotated = not self.rotated
        self.draw_board()

    def cancel_animation(self):
        if self.animation_job is not None:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None
        self.animation = None
        self.animating = False

    def close(self):
        self.cancel_animation()
        if self.ai_job is not None:
            self.root.after_cancel(self.ai_job)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    game = ChessGame(root)
    root.mainloop()
