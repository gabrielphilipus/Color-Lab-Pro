import math
import tkinter as tk
from tkinter import simpledialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw
import pyautogui
import time

def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return [int(hex_code[i:i+2], 16) for i in (0, 2, 4)]

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

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

# CLASSE PRINCIPAL

class AppCores:
    def __init__(self, root):
        self.root = root
        self.root.title("Color Lab Pro")
        self.root.geometry("800x550")
        self.root.attributes("-topmost", True)
        
        self.cores_hex = []
        self.cor_atual = "#0078d7"
        self.passo_delta = 1.5 #mais = pixelização / menos = suavização

        # --- Interface ---
        frame_menu = tk.Frame(self.root, pady=15)
        frame_menu.pack(side=tk.TOP, fill=tk.X)

        tk.Button(frame_menu, text="⌨️ HEX", command=self.ferramenta_digitar, width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(frame_menu, text="🎨 Seletor", command=self.ferramenta_seletor, width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(frame_menu, text="🧪 Conta-Gotas", command=self.ferramenta_conta_gotas, width=12, bg="#e3f2fd").pack(side=tk.LEFT, padx=10)

        self.label_info = tk.Label(self.root, text="Clique no gradiente para copiar", fg="gray")
        self.label_info.pack()

        self.canvas = tk.Canvas(self.root, bg="#f0f0f0", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.canvas.bind("<Configure>", lambda e: self.desenhar_gradiente())
        self.canvas.bind("<Button-1>", self.copiar_clique)

        self.gerar_lista_cores(self.cor_atual)

    # Conta-Gotas
    def ferramenta_conta_gotas(self):
        self.root.withdraw()
        self.root.update_idletasks()
        time.sleep(0.2)
        
        # Captura do Desktop
        self.print_tela = pyautogui.screenshot()
        larg_t, alt_t = self.print_tela.size
        
        overlay = tk.Toplevel()
        overlay.attributes("-fullscreen", True, "-topmost", True)
        overlay.config(cursor="tcross") #crosshair,tcross,circle,dot,target,plus,hand2,none
        
        canvas_ov = tk.Canvas(overlay, highlightthickness=0, borderwidth=0)
        canvas_ov.pack(fill="both", expand=True)
        
        self.img_bg = ImageTk.PhotoImage(self.print_tela)
        canvas_ov.create_image(0, 0, anchor="nw", image=self.img_bg)

        # Config da Lupa
        lupa_size = 150 #Tamanho da lupa conta gotas
        zoom = 10 #Zoom da lupa conta gotas
        lupa_label = tk.Label(overlay, bd=1, relief="solid", bg="black")
        lupa_label.place(x=-200, y=-200)

        def atualizar_lupa(event):
            x, y = event.x, event.y
            
            # Recorte e Zoom
            raio = (lupa_size // zoom) // 2
            box = (x - raio, y - raio, x + raio, y + raio)
            recorte = self.print_tela.crop(box)
            zoom_img = recorte.resize((lupa_size, lupa_size), Image.NEAREST) #NEAREST,BILINEAR,BICUBIC,LANCZOS
            
            # --- Desenhar Feedback Visual na Lupa ---
            draw = ImageDraw.Draw(zoom_img)
            meio = lupa_size // 2
            
            # Mira central
            draw.line([meio, 0, meio, lupa_size], fill="red", width=1)
            draw.line([0, meio, lupa_size, meio], fill="red", width=1)
            
            # Ícone de conta-gotas simbólico no canto da lupa
            # (Um pequeno quadrado com a cor atual do pixel)
            pixel_color = self.print_tela.getpixel((x, y))
            draw.rectangle([5, 5, 45, 25], fill="white", outline="black")
            draw.text((8, 8), rgb_to_hex(pixel_color), fill="black")
            
            # Atualizar Imagem
            img_lupa = ImageTk.PhotoImage(zoom_img)
            lupa_label.config(image=img_lupa)
            lupa_label.image = img_lupa
            
            # Posicionamento (seguindo o mouse com offset)
            offset = 20
            nx = x + offset if x + lupa_size + offset < larg_t else x - lupa_size - offset
            ny = y + offset if y + lupa_size + offset < alt_t else y - lupa_size - offset
            lupa_label.place(x=nx, y=ny)

        def capturar(event):
            c_rgb = self.print_tela.getpixel((event.x, event.y))
            overlay.destroy()
            self.root.deiconify()
            self.gerar_lista_cores(rgb_to_hex(c_rgb))

        canvas_ov.bind("<Motion>", atualizar_lupa)
        canvas_ov.bind("<Button-1>", capturar)
        overlay.bind("<Escape>", lambda e: [overlay.destroy(), self.root.deiconify()])

    # --- Funções de Gradiente (Responsivas) ---
    def gerar_lista_cores(self, hex_base):
        self.cor_atual = hex_base
        try:
            lab_alvo = xyz_to_lab(rgb_to_xyz(hex_to_rgb(hex_base)))
            pontos = [(0,0,0), lab_alvo, (100,0,0)]
            self.cores_hex = []
            
            for i in range(len(pontos)-1):
                ini, fim = pontos[i], pontos[i+1]
                dist = delta_e_cie76(ini, fim)
                passos = max(1, int(dist / self.passo_delta))
                for p in range(passos):
                    t = p / passos
                    curr = tuple(ini[j] + (fim[j]-ini[j])*t for j in range(3))
                    self.cores_hex.append(rgb_to_hex(xyz_to_rgb(lab_to_xyz(curr))))
            
            self.desenhar_gradiente()
            self.label_info.config(text=f"Base: {hex_base} | {len(self.cores_hex)} tons", fg="black")
        except:
            messagebox.showerror("Erro", "HEX Inválido")

    def desenhar_gradiente(self):
        if not self.cores_hex: return
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1: w = 760
        
        largura_f = w / len(self.cores_hex)
        self.largura_faixa_atual = largura_f
        
        for i, c in enumerate(self.cores_hex):
            x1 = i * largura_f
            x2 = (i + 1) * largura_f
            self.canvas.create_rectangle(x1, 0, x2, h, fill=c, outline=c)

    def ferramenta_digitar(self):
        cor = simpledialog.askstring("Input", "HEX:", parent=self.root)
        if cor:
            if not cor.startswith('#'): cor = '#' + cor
            self.gerar_lista_cores(cor)

    def ferramenta_seletor(self):
        cor = colorchooser.askcolor(title="Seletor", parent=self.root)
        if cor[1]: self.gerar_lista_cores(cor[1])

    def copiar_clique(self, event):
        if not self.cores_hex: return
        idx = int(event.x // self.largura_faixa_atual)
        if idx < len(self.cores_hex):
            c = self.cores_hex[idx]
            self.root.clipboard_clear()
            self.root.clipboard_append(c)
            self.label_info.config(text=f"Copiado: {c}", fg="#2e7d32", font=("Arial", 9, "bold"))

if __name__ == "__main__":
    root = tk.Tk()
    app = AppCores(root)
    root.mainloop()