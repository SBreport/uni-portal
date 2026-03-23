"""논문 분석 GUI — 더블클릭으로 실행.

.pyw 확장자: 콘솔 창 없이 GUI만 표시.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import sys
import glob

# 프로젝트 루트
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT, "paper_results")


class PaperAnalyzerGUI:
    def __init__(self):
        self.win = tk.Tk()
        self.win.title("논문 분석 도구")
        self.win.geometry("620x580")
        self.win.resizable(False, False)
        self.win.configure(bg="#f8fafc")

        self.running = False
        self.build_ui()

    def build_ui(self):
        w = self.win

        # ── 헤더 ──
        hdr = tk.Frame(w, bg="#1e40af", height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔬 논문 PDF 분석 도구", font=("맑은 고딕", 14, "bold"),
                 fg="white", bg="#1e40af").pack(side="left", padx=16)

        body = tk.Frame(w, bg="#f8fafc", padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # ── STEP 1: 폴더 선택 ──
        self._section(body, "STEP 1", "분석할 논문 폴더 선택")

        folder_frame = tk.Frame(body, bg="#f8fafc")
        folder_frame.pack(fill="x", pady=(0, 4))

        self.folder_var = tk.StringVar()
        self.folder_entry = tk.Entry(folder_frame, textvariable=self.folder_var,
                                     font=("맑은 고딕", 10), relief="solid", bd=1)
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=4)

        tk.Button(folder_frame, text="📂 폴더 찾기", font=("맑은 고딕", 9),
                  command=self.browse_folder, bg="#475569", fg="white",
                  relief="flat", padx=12, pady=4).pack(side="right", padx=(8, 0))

        self.pdf_label = tk.Label(body, text="", font=("맑은 고딕", 9),
                                  fg="#64748b", bg="#f8fafc", anchor="w")
        self.pdf_label.pack(fill="x", pady=(0, 12))

        # ── STEP 2: API 키 ──
        self._section(body, "STEP 2", "Anthropic API 키 입력")

        self.key_var = tk.StringVar()
        key_entry = tk.Entry(body, textvariable=self.key_var, show="●",
                             font=("맑은 고딕", 10), relief="solid", bd=1)
        key_entry.pack(fill="x", ipady=4, pady=(0, 4))

        tk.Label(body, text="sk-ant-api03-... 형태의 키를 입력하세요",
                 font=("맑은 고딕", 8), fg="#94a3b8", bg="#f8fafc",
                 anchor="w").pack(fill="x", pady=(0, 12))

        # ── STEP 3: 옵션 ──
        self._section(body, "STEP 3", "분석 옵션")

        opt_frame = tk.Frame(body, bg="#f8fafc")
        opt_frame.pack(fill="x", pady=(0, 12))

        self.test_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt_frame, text="테스트 모드 (DB 저장 안 함)",
                       variable=self.test_var, font=("맑은 고딕", 9),
                       bg="#f8fafc", activebackground="#f8fafc").pack(side="left")

        self.time_label = tk.Label(opt_frame, text="", font=("맑은 고딕", 9),
                                   fg="#64748b", bg="#f8fafc")
        self.time_label.pack(side="right")

        # ── 실행 버튼 ──
        self.run_btn = tk.Button(body, text="▶ 분석 시작", font=("맑은 고딕", 12, "bold"),
                                 command=self.start_analysis, bg="#059669", fg="white",
                                 relief="flat", padx=20, pady=8, cursor="hand2")
        self.run_btn.pack(fill="x", pady=(4, 12))

        # ── 진행 로그 ──
        self._section(body, "", "진행 상황")

        self.log = scrolledtext.ScrolledText(body, height=10, font=("Consolas", 9),
                                              relief="solid", bd=1, state="disabled",
                                              bg="white")
        self.log.pack(fill="both", expand=True)

        # ── 하단 버튼 ──
        btn_frame = tk.Frame(body, bg="#f8fafc")
        btn_frame.pack(fill="x", pady=(8, 0))

        self.open_btn = tk.Button(btn_frame, text="📁 결과 폴더 열기",
                                  font=("맑은 고딕", 9), command=self.open_results,
                                  bg="#e2e8f0", relief="flat", padx=12, pady=4,
                                  state="disabled")
        self.open_btn.pack(side="left")

        tk.Label(btn_frame, text="완료 후 웹앱에서 JSON 업로드 →  시술정보 > 시술논문 > JSON 업로드",
                 font=("맑은 고딕", 8), fg="#94a3b8", bg="#f8fafc").pack(side="right")

    def _section(self, parent, step, title):
        f = tk.Frame(parent, bg="#f8fafc")
        f.pack(fill="x", pady=(0, 4))
        if step:
            tk.Label(f, text=step, font=("맑은 고딕", 8, "bold"), fg="#3b82f6",
                     bg="#dbeafe", padx=6, pady=1).pack(side="left")
        tk.Label(f, text=f"  {title}", font=("맑은 고딕", 10, "bold"),
                 fg="#334155", bg="#f8fafc").pack(side="left")

    def browse_folder(self):
        path = filedialog.askdirectory(title="논문 PDF 폴더 선택")
        if path:
            self.folder_var.set(path)
            self.check_pdfs(path)

    def check_pdfs(self, path):
        pdfs = glob.glob(os.path.join(path, "*.pdf"))
        count = len(pdfs)
        if count:
            self.pdf_label.config(text=f"✅ PDF {count}건 발견", fg="#059669")
            self.time_label.config(text=f"예상 소요: 약 {count}분")
        else:
            self.pdf_label.config(text="❌ PDF 파일이 없습니다", fg="#dc2626")
            self.time_label.config(text="")

    def log_append(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def start_analysis(self):
        folder = self.folder_var.get().strip()
        api_key = self.key_var.get().strip()

        if not folder:
            messagebox.showwarning("알림", "폴더를 선택해주세요.")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("오류", f"폴더가 존재하지 않습니다:\n{folder}")
            return
        if not api_key:
            messagebox.showwarning("알림", "API 키를 입력해주세요.")
            return
        if not api_key.startswith("sk-"):
            messagebox.showwarning("알림", "올바른 API 키 형식이 아닙니다.\nsk-ant-... 형태여야 합니다.")
            return

        self.running = True
        self.run_btn.config(state="disabled", text="⏳ 분석 중... (창을 닫지 마세요)")
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

        thread = threading.Thread(target=self.run_analysis, args=(folder, api_key), daemon=True)
        thread.start()

    def run_analysis(self, folder, api_key):
        try:
            cmd = [sys.executable, os.path.join(ROOT, "paper_analyzer.py"),
                   "--dir", folder]
            if self.test_var.get():
                cmd.append("--dry-run")

            env = os.environ.copy()
            env["ANTHROPIC_API_KEY"] = api_key

            self.log_append(f"폴더: {folder}")
            self.log_append(f"모드: {'테스트' if self.test_var.get() else '실제 분석'}")
            self.log_append("=" * 50)
            self.log_append("")

            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                env=env, cwd=ROOT
            )

            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    self.win.after(0, self.log_append, line)

            proc.wait()

            self.win.after(0, self.log_append, "")
            if proc.returncode == 0:
                self.win.after(0, self.log_append, "✅ 분석 완료!")
                self.win.after(0, self.log_append, "")
                self.win.after(0, self.log_append, "다음 단계: 웹앱 > 시술정보 > 시술논문 > JSON 업로드")
                self.win.after(0, lambda: self.open_btn.config(state="normal"))
            else:
                self.win.after(0, self.log_append, f"⚠️ 종료 코드: {proc.returncode}")

        except Exception as e:
            self.win.after(0, self.log_append, f"오류: {e}")
        finally:
            self.running = False
            self.win.after(0, lambda: self.run_btn.config(
                state="normal", text="▶ 분석 시작"))

    def open_results(self):
        if os.path.isdir(RESULTS_DIR):
            os.startfile(RESULTS_DIR)
        else:
            messagebox.showinfo("알림", "결과 폴더가 아직 생성되지 않았습니다.")

    def run(self):
        self.win.mainloop()


if __name__ == "__main__":
    app = PaperAnalyzerGUI()
    app.run()
