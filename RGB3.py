import math
import tkinter as tk
from tkinter import simpledialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw
import pyautogui
import time
import colorsys
import json
import os

def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return [int(hex_code[i:i+2], 16) for i in (0, 2, 4)]

def rgb_to_hex(rgb):
    r, g, b = [max(0, min(255, int(v))) for v in rgb]
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)

def rgb_to_xyz(rgb):
    res = []
    for c in rgb:
        v = c / 255.0
        v = pow((v + 0.055) / 1.055, 2.4) if v > 0.04045 else v / 12.92
        res.append(v * 100)
    return (res[0] * 0.4124 + res[1] * 0.3576 + res[2] * 0.1805,
            res[0] * 0.2126 + res[1] * 0.7152 + res[2] * 0.0722,
            res[0] * 0.0193 + res[1] * 0.1192 + res[2] * 0.9505)

def xyz_to_lab(xyz):
    ref = (95.047, 100.000, 108.883)
    res = [pow(v/r, 1/3) if v/r > 0.008856 else (7.787*(v/r))+(16/116) for v, r in zip(xyz, ref)]
    return ((116 * res[1]) - 16, 500 * (res[0] - res[1]), 200 * (res[1] - res[2]))

def lab_to_xyz(lab):
    y = (lab[0] + 16) / 116
    x, z = lab[1]/500 + y, y - lab[2]/200
    res = [pow(v, 3) if v**3 > 0.008856 else (v - 16/116)/7.787 for v in [x, y, z]]
    ref = (95.047, 100.000, 108.883)
    return (res[0]*ref[0], res[1]*ref[1], res[2]*ref[2])

def xyz_to_rgb(xyz):
    x, y, z = [v / 100 for v in xyz]
    r, g, b = x*3.2406 + y*-1.5372 + z*-0.4986, x*-0.9689 + y*1.8758 + z*0.0415, x*0.0557 + y*-0.2040 + z*1.0570
    res = [max(0, min(1, v)) for v in [r, g, b]]
    res = [1.055 * pow(v, 1/2.4) - 0.055 if v > 0.0031308 else 12.92 * v for v in res]
    return [max(0, min(255, v * 255)) for v in res]

def delta_e_cie76(l1, l2):
    return math.sqrt(sum((a-b)**2 for a, b in zip(l1, l2)))

def kelvin_to_rgb(kelvin):
    temp = kelvin / 100
    if temp <= 66:
        r = 255
        g = max(0, min(255, 99.47 * math.log(temp) - 161.12))
        b = 0 if temp <= 19 else max(0, min(255, 138.52 * math.log(temp - 10) - 305.04))
    else:
        r = max(0, min(255, 329.70 * pow(temp - 60, -0.1332)))
        g = max(0, min(255, 288.12 * pow(temp - 60, -0.0755)))
        b = 255
    return (r/255, g/255, b/255)

def simular_daltonismo(rgb_linear, tipo):
    rl, gl, bl = rgb_linear
    if tipo == "deuteranopia": return [0.625*rl + 0.375*gl, 0.7*rl + 0.3*gl, 0.3*gl + 0.7*bl]
    if tipo == "protanopia": return [0.567*rl + 0.433*gl, 0.558*rl + 0.442*gl, 0.242*gl + 0.758*bl]
    if tipo == "tritanopia": return [0.95*rl + 0.05*gl, 0.433*gl + 0.567*bl, 0.475*gl + 0.525*bl]
    if tipo == "acromatopsia":
        lum = 0.2126*rl + 0.7152*gl + 0.0722*bl
        return [lum, lum, lum]
    return rgb_linear

#CLASSE PRINCIPAL

class AppCores:
    def __init__(self, root):
        self.root = root
        self.root.title("Color Lab Pro")
        self.root.geometry("850x600")
        self.root.attributes("-topmost", True)
        
        # Variáveis de Controle
        self.cores_hex = []
        self.cor_atual = "#0078d7"
        self.passo_delta = tk.DoubleVar(value=1.5)
        self.tema = tk.StringVar(value="claro")
        self.sim_daltonismo = tk.StringVar(value="normal")
        self.config_win = None
        
        # Ajustes de Imagem
        self.adj_bright = tk.DoubleVar(value=0)
        self.adj_contrast = tk.DoubleVar(value=1.0)
        self.adj_gamma = tk.DoubleVar(value=1.0)
        self.adj_sat = tk.DoubleVar(value=1.0)
        self.adj_hue = tk.DoubleVar(value=0)
        self.adj_temp = tk.DoubleVar(value=6500)

        self.arquivo_config = "config.json"
        self.paletas = {
            "claro": { "window_bg": "#ffffff", "text_fg": "#000000", "btn": "#e1e1e1", "special": "#e3f2fd", "canvas": "#f0f0f0" },
            "escuro": { "window_bg": "#1e1e1e", "text_fg": "#ffffff", "btn": "#333333", "special": "#2196f3", "canvas": "#121212" }
        }

        self.carregar_configuracoes()

        self.frame_menu = tk.Frame(self.root, pady=15)
        self.frame_menu.pack(side=tk.TOP, fill=tk.X)

        tk.Button(self.frame_menu, text="⌨️ HEX", command=self.ferramenta_digitar, width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(self.frame_menu, text="🎨 Seletor", command=self.ferramenta_seletor, width=12).pack(side=tk.LEFT, padx=10)
        self.btn_gotas = tk.Button(self.frame_menu, text="🧪 Conta-Gotas", command=self.ferramenta_conta_gotas, width=12)
        self.btn_gotas.pack(side=tk.LEFT, padx=10)
        tk.Button(self.frame_menu, text="⚙️ Config", command=self.abrir_configuracoes, width=12).pack(side=tk.RIGHT, padx=10)

        self.label_info = tk.Label(self.root, text="Color Lab Pro v4.6")
        self.label_info.pack()

        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.canvas.bind("<Configure>", lambda e: self.desenhar_gradiente())
        self.canvas.bind("<Button-1>", self.copiar_clique)

        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        self.aplicar_tema()
        self.gerar_lista_cores(self.cor_atual)

    # SALVAMENTO
    def salvar_configuracoes(self):
        try:
            config_data = {
                "tema": self.tema.get(),
                "sim_daltonismo": self.sim_daltonismo.get(),
                "passo_delta": self.passo_delta.get(),
                "brilho": self.adj_bright.get(),
                "contraste": self.adj_contrast.get(),
                "gamma": self.adj_gamma.get(),
                "saturacao": self.adj_sat.get(),
                "matiz": self.adj_hue.get(),
                "temperatura": self.adj_temp.get(),
                "ultima_cor": self.cor_atual
            }
            with open(self.arquivo_config, "w") as f:
                json.dump(config_data, f, indent=4)
        except: pass

    def carregar_configuracoes(self):
        if os.path.exists(self.arquivo_config):
            try:
                with open(self.arquivo_config, "r") as f:
                    data = json.load(f)
                    self.tema.set(data.get("tema", "claro"))
                    self.sim_daltonismo.set(data.get("sim_daltonismo", "normal"))
                    self.passo_delta.set(data.get("passo_delta", 1.5))
                    self.adj_bright.set(data.get("brilho", 0))
                    self.adj_contrast.set(data.get("contraste", 1.0))
                    self.adj_gamma.set(data.get("gamma", 1.0))
                    self.adj_sat.set(data.get("saturacao", 1.0))
                    self.adj_hue.set(data.get("matiz", 0))
                    self.adj_temp.set(data.get("temperatura", 6500))
                    self.cor_atual = data.get("ultima_cor", "#0078d7")
            except: pass

    def ao_fechar(self):
        self.salvar_configuracoes()
        self.root.destroy()

    # NAVEGAÇÃO CONFIGS
    def abrir_configuracoes(self):
        if self.config_win is None or not tk.Toplevel.winfo_exists(self.config_win):
            self.config_win = tk.Toplevel(self.root)
            self.config_win.title("Configurações")
            self.config_win.geometry("450x680")
            self.config_win.attributes("-topmost", True)
            self.config_container = tk.Frame(self.config_win)
            self.config_container.pack(fill=tk.BOTH, expand=True)
            self.tela_menu_config()
            # Salva ao fechar a janela de config também
            self.config_win.protocol("WM_DELETE_WINDOW", lambda: [self.salvar_configuracoes(), self.config_win.destroy()])
        else:
            self.config_win.focus_set()

    def tela_menu_config(self):
        for w in self.config_container.winfo_children(): w.destroy()
        p = self.paletas[self.tema.get()]
        self.config_win.config(bg=p["window_bg"])
        self.config_container.config(bg=p["window_bg"])
        tk.Label(self.config_container, text="MENU", font=("Arial", 12, "bold")).pack(pady=30)
        tk.Button(self.config_container, text="🖥️ Interface", command=self.tela_interface, width=25).pack(pady=10)
        tk.Button(self.config_container, text="🎞️ Ajustes", command=self.tela_ajustes, width=25).pack(pady=10)
        tk.Button(self.config_container, text="👁️ Acessibilidade", command=self.tela_modos, width=25).pack(pady=10)
        self.aplicar_tema()

    def tela_interface(self):
        for w in self.config_container.winfo_children(): w.destroy()
        tk.Button(self.config_container, text="⬅ Voltar", command=self.tela_menu_config).pack(anchor=tk.NW, padx=10, pady=10)
        tk.Label(self.config_container, text="TEMA", font=("Arial", 11, "bold")).pack(pady=10)
        tk.Radiobutton(self.config_container, text="Claro", variable=self.tema, value="claro", command=self.aplicar_tema).pack(pady=5)
        tk.Radiobutton(self.config_container, text="Escuro", variable=self.tema, value="escuro", command=self.aplicar_tema).pack(pady=5)
        self.aplicar_tema()

    def tela_ajustes(self):
        for w in self.config_container.winfo_children(): w.destroy()
        tk.Button(self.config_container, text="⬅ Voltar", command=self.tela_menu_config).pack(anchor=tk.NW, padx=10, pady=10)
        tk.Label(self.config_container, text="AJUSTES", font=("Arial", 11, "bold")).pack(pady=5)
        
        # Função auxiliar de slider otimizada para tempo real
        def sld(l, v, d, a, r, is_delta=False):
            tk.Label(self.config_container, text=l).pack()
            cmd = lambda e: self.gerar_lista_cores(self.cor_atual) if is_delta else self.desenhar_gradiente()
            tk.Scale(self.config_container, from_=d, to=a, resolution=r, orient=tk.HORIZONTAL, variable=v, command=cmd, highlightthickness=0).pack(fill=tk.X, padx=40)
        
        sld("Brilho", self.adj_bright, -100, 100, 1)
        sld("Contraste", self.adj_contrast, 0.5, 2.0, 0.05)
        sld("Gamma", self.adj_gamma, 0.1, 3.0, 0.1)
        sld("Saturação", self.adj_sat, 0.0, 2.0, 0.1)
        sld("Matiz", self.adj_hue, -180, 180, 1)
        sld("Temperatura", self.adj_temp, 1000, 12000, 100)
        sld("Nitidez", self.passo_delta, 0.1, 10.0, 0.1, is_delta=True)
        
        tk.Button(self.config_container, text="🔄 Restaurar Padrões", command=self.resetar_ajustes, bg="#ffcdd2", fg="black").pack(pady=20)
        self.aplicar_tema()

    def tela_modos(self):
        for w in self.config_container.winfo_children(): w.destroy()
        tk.Button(self.config_container, text="⬅ Voltar", command=self.tela_menu_config).pack(anchor=tk.NW, padx=10, pady=10)
        tk.Label(self.config_container, text="MODOS", font=("Arial", 11, "bold")).pack(pady=10)
        for t, v in [("Normal", "normal"), ("Deuteranopia (Verde-Vermelho)", "deuteranopia"), ("Protanopia (Vermelho-Verde)", "protanopia"), ("Tritanopia (Azul-Amarelo)", "tritanopia"), ("Acromatopsia (Monocromacia)", "acromatopsia")]:
            tk.Radiobutton(self.config_container, text=t, variable=self.sim_daltonismo, value=v, command=self.desenhar_gradiente).pack(anchor=tk.W, padx=100, pady=5)
        self.aplicar_tema()

    def resetar_ajustes(self):
        self.adj_bright.set(0); self.adj_contrast.set(1.0); self.adj_gamma.set(1.0); self.adj_sat.set(1.0); self.adj_hue.set(0); self.adj_temp.set(6500); self.passo_delta.set(1.5); self.sim_daltonismo.set("normal")
        self.gerar_lista_cores(self.cor_atual); self.salvar_configuracoes()

    # FERRAMENTAS 
    def ferramenta_conta_gotas(self):
        self.root.withdraw(); time.sleep(0.2); print_tela = pyautogui.screenshot(); larg_t, alt_t = print_tela.size
        overlay = tk.Toplevel(); overlay.attributes("-fullscreen", True, "-topmost", True); overlay.config(cursor="tcross") 
        canvas_ov = tk.Canvas(overlay, highlightthickness=0); canvas_ov.pack(fill="both", expand=True)
        img_bg = ImageTk.PhotoImage(print_tela); canvas_ov.create_image(0, 0, anchor="nw", image=img_bg)
        lupa_size, zoom = 180, 10; mask = Image.new('L', (lupa_size, lupa_size), 0); ImageDraw.Draw(mask).ellipse((0, 0, lupa_size, lupa_size), fill=255)
        def atualizar_lupa(event):
            x, y = event.x, event.y; raio = (lupa_size // zoom) // 2; box = (x - raio, y - raio, x + raio, y + raio); recorte = print_tela.crop(box)
            zoom_img = recorte.resize((lupa_size, lupa_size), Image.NEAREST).convert("RGBA"); zoom_img.putalpha(mask)
            draw = ImageDraw.Draw(zoom_img); meio = lupa_size // 2; draw.line([meio, 0, meio, lupa_size], fill="red", width=1); draw.line([0, meio, lupa_size, meio], fill="red", width=1)
            px_color = print_tela.getpixel((x, y)); draw.rectangle([meio-30, meio+20, meio+30, meio+40], fill="white", outline="black"); draw.text((meio-22, meio+24), rgb_to_hex(px_color), fill="black")
            img_lupa = ImageTk.PhotoImage(zoom_img); canvas_ov.delete("lupa_dinamica")
            nx = x + 30 if x + lupa_size + 30 < larg_t else x - lupa_size - 30; ny = y + 30 if y + lupa_size + 30 < alt_t else y - lupa_size - 30
            canvas_ov.create_image(nx, ny, anchor="nw", image=img_lupa, tag="lupa_dinamica"); canvas_ov.create_oval(nx, ny, nx+lupa_size, ny+lupa_size, outline="black", width=2, tag="lupa_dinamica"); canvas_ov.img_ref = img_lupa
        def capturar(event):
            c = rgb_to_hex(print_tela.getpixel((event.x, event.y))); overlay.destroy(); self.root.deiconify(); self.gerar_lista_cores(c); self.salvar_configuracoes()
        canvas_ov.bind("<Motion>", atualizar_lupa); canvas_ov.bind("<Button-1>", capturar)
        overlay.bind("<Escape>", lambda e:[overlay.destroy(), self.root.deiconify()]); overlay.img_ref = img_bg

    def aplicar_tema(self, event=None):
        p = self.paletas[self.tema.get()]; self.root.config(bg=p["window_bg"]); self.frame_menu.config(bg=p["window_bg"]); self.canvas.config(bg=p["canvas"]); self.label_info.config(bg=p["window_bg"], fg=p["text_fg"])
        for w in self.frame_menu.winfo_children():
            if isinstance(w, tk.Button): w.config(bg=p["btn"] if w.cget("text") != "🧪 Conta-Gotas" else p["special"], fg=p["text_fg"])
        if self.config_win and tk.Toplevel.winfo_exists(self.config_win):
            self.config_win.config(bg=p["window_bg"]); self.config_container.config(bg=p["window_bg"])
            def upd(parent):
                for c in parent.winfo_children():
                    if isinstance(c, (tk.Label, tk.Radiobutton, tk.Scale, tk.Frame)):
                        try: c.config(bg=p["window_bg"], fg=p["text_fg"])
                        except: pass
                    if isinstance(c, tk.Button) and c.cget("text") != "🔄 Restaurar Padrões": c.config(bg=p["btn"], fg=p["text_fg"])
                    upd(c)
            upd(self.config_win)
        if self.cores_hex: self.desenhar_gradiente()

    # RENDERIZAÇÃO TEMPO REAL
    def desenhar_gradiente(self):
        if not self.cores_hex: return
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1: w = 760
        if h <= 1: h = 400
            
        larg_f = w / len(self.cores_hex)
        # Cache de valores para performance
        bright = self.adj_bright.get()
        contrast = self.adj_contrast.get()
        gamma = self.adj_gamma.get()
        sat_val = self.adj_sat.get()
        hue_val = self.adj_hue.get()
        temp_val = self.adj_temp.get()
        daltonismo = self.sim_daltonismo.get()
        tr, tg, tb = kelvin_to_rgb(temp_val)

        for i, c in enumerate(self.cores_hex):
            rgb = hex_to_rgb(c)
            r, g, b = [v/255.0 for v in rgb]
            # Temperatura
            r, g, b = r*tr, g*tg, b*tb
            # HSL
            hue, l, sat = colorsys.rgb_to_hls(r, g, b)
            r, g, b = colorsys.hls_to_rgb((hue + hue_val/360.0)%1.0, l, max(0, min(1, sat*sat_val)))
            # Gamma
            r, g, b = [pow(v, gamma) for v in [r, g, b]]
            # Contraste/Brilho
            r, g, b = [(v-0.5)*contrast + 0.5 + (bright/255.0) for v in [r, g, b]]
            # Simulação
            rgb_sim = simular_daltonismo([max(0, min(1, v)) for v in [r, g, b]], daltonismo)
            hex_f = rgb_to_hex([v*255 for v in rgb_sim])
            self.canvas.create_rectangle(i*larg_f, 0, (i+1)*larg_f, h, fill=hex_f, outline=hex_f)

    def gerar_lista_cores(self, hex_base):
        self.cor_atual = hex_base
        try:
            lab_alvo = xyz_to_lab(rgb_to_xyz(hex_to_rgb(hex_base))); pontos = [(0,0,0), lab_alvo, (100,0,0)]; self.cores_hex = []
            for i in range(len(pontos)-1):
                ini, fim = pontos[i], pontos[i+1]; dist = delta_e_cie76(ini, fim); passos = max(1, int(dist / self.passo_delta.get()))
                for p in range(passos):
                    t = p / passos; curr = tuple(ini[j] + (fim[j]-ini[j])*t for j in range(3)); self.cores_hex.append(rgb_to_hex(xyz_to_rgb(lab_to_xyz(curr))))
            self.desenhar_gradiente()
        except: pass

    def ferramenta_digitar(self):
        cor = simpledialog.askstring("Input", "HEX:", parent=self.root)
        if cor: self.gerar_lista_cores('#' + cor.lstrip('#'))

    def ferramenta_seletor(self):
        cor = colorchooser.askcolor(title="Seletor")[1]
        if cor: self.gerar_lista_cores(cor)

    def copiar_clique(self, event):
        w = self.canvas.winfo_width(); larg_f = w / len(self.cores_hex); idx = int(event.x // larg_f)
        if idx < len(self.cores_hex):
            c = self.cores_hex[idx]; self.root.clipboard_clear(); self.root.clipboard_append(c); self.label_info.config(text=f"Copiado: {c}", fg="#2e7d32")

if __name__ == "__main__":
    root = tk.Tk(); app = AppCores(root); root.mainloop()