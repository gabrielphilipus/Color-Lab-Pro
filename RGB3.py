import math
import tkinter as tk
from tkinter import simpledialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw
import pyautogui

# --- Matemática de Cores (CIELAB) continua a mesma ---
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
    return [v * 255 for v in res]

def delta_e_cie76(l1, l2):
    return math.sqrt(sum((a-b)**2 for a, b in zip(l1, l2)))

# --- Interface Principal ---
class AppCores:
    def __init__(self, root):
        self.root = root
        self.root.title("Color Lab Pro - Responsive")
        self.root.geometry("800x500")
        self.root.attributes("-topmost", True)
        
        self.cores_hex = []
        self.cor_atual = "#0078d7"
        self.passo = 1.5

        # Menu
        frame_menu = tk.Frame(self.root, pady=10)
        frame_menu.pack(side=tk.TOP, fill=tk.X)

        tk.Button(frame_menu, text="⌨️ HEX", command=self.ferramenta_digitar).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_menu, text="🎨 Seletor", command=self.ferramenta_seletor).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_menu, text="🧪 Conta-Gotas", command=self.ferramenta_conta_gotas, bg="#e3f2fd").pack(side=tk.LEFT, padx=5)

        self.label_info = tk.Label(self.root, text="Ajuste o tamanho da janela para ver o efeito", fg="gray")
        self.label_info.pack()

        # Canvas Responsivo
        # expand=True e fill=tk.BOTH fazem o canvas ocupar todo o espaço restante
        self.canvas = tk.Canvas(self.root, bg="#f0f0f0", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Binding de Redimensionamento
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Button-1>", self.copiar_clique)

        self.gerar_lista_cores(self.cor_atual)

    def on_resize(self, event):
        """Chamado toda vez que a janela muda de tamanho."""
        self.desenhar_gradiente()

    def gerar_lista_cores(self, hex_base):
        """Calcula a matemática das cores apenas uma vez por nova cor."""
        self.cor_atual = hex_base
        try:
            lab_alvo = xyz_to_lab(rgb_to_xyz(hex_to_rgb(hex_base)))
            pontos = [(0,0,0), lab_alvo, (100,0,0)]
            self.cores_hex = []
            
            for i in range(len(pontos)-1):
                ini, fim = pontos[i], pontos[i+1]
                dist = delta_e_cie76(ini, fim)
                passos = max(1, int(dist / self.passo))
                for p in range(passos):
                    t = p / passos
                    curr = tuple(ini[j] + (fim[j]-ini[j])*t for j in range(3))
                    self.cores_hex.append(rgb_to_hex(xyz_to_rgb(lab_to_xyz(curr))))
            
            self.desenhar_gradiente()
            self.label_info.config(text=f"Base: {hex_base} | {len(self.cores_hex)} tons", fg="black")
        except:
            messagebox.showerror("Erro", "Cor inválida")

    def desenhar_gradiente(self):
        """Renderiza as cores baseando-se na largura ATUAL do canvas."""
        if not self.cores_hex: return
        
        self.canvas.delete("all")
        largura_canvas = self.canvas.winfo_width()
        altura_canvas = self.canvas.winfo_height()
        
        # Calcula a largura de cada faixa de cor dinamicamente
        largura_faixa = largura_canvas / len(self.cores_hex)
        
        for i, c in enumerate(self.cores_hex):
            x1 = i * largura_faixa
            x2 = (i + 1) * largura_faixa
            self.canvas.create_rectangle(x1, 0, x2, altura_canvas, fill=c, outline=c)

    def ferramenta_digitar(self):
        cor = simpledialog.askstring("Input", "Digite o código HEX:", parent=self.root)
        if cor:
            if not cor.startswith('#'): cor = '#' + cor
            self.gerar_lista_cores(cor)

    def ferramenta_seletor(self):
        cor = colorchooser.askcolor(title="Seletor", parent=self.root)
        if cor[1]: self.gerar_lista_cores(cor[1])

    def ferramenta_conta_gotas(self):
        self.root.withdraw()
        import time
        time.sleep(0.3)
        print_tela = pyautogui.screenshot()
        self.overlay = tk.Toplevel()
        self.overlay.attributes("-fullscreen", True, "-topmost", True)
        self.overlay.config(cursor="crosshair")
        self.img_overlay = ImageTk.PhotoImage(print_tela)
        canvas_ov = tk.Canvas(self.overlay, highlightthickness=0)
        canvas_ov.pack(fill="both", expand=True)
        canvas_ov.create_image(0, 0, anchor="nw", image=self.img_overlay)
        
        def capturar(event):
            c_rgb = print_tela.getpixel((event.x, event.y))
            h_res = rgb_to_hex(c_rgb)
            self.overlay.destroy()
            self.root.deiconify()
            self.gerar_lista_cores(h_res)

        canvas_ov.bind("<Button-1>", capturar)
        self.overlay.bind("<Escape>", lambda e: [self.overlay.destroy(), self.root.deiconify()])

    def copiar_clique(self, event):
        largura_canvas = self.canvas.winfo_width()
        largura_faixa = largura_canvas / len(self.cores_hex)
        idx = int(event.x // largura_faixa)
        if idx < len(self.cores_hex):
            c = self.cores_hex[idx]
            self.root.clipboard_clear()
            self.root.clipboard_append(c)
            self.label_info.config(text=f"Copiado: {c}", fg="#2e7d32")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppCores(root)
    root.mainloop()