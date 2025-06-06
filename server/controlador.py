import os
import sys
import logging
import tkinter as tk
import customtkinter as ctk
import threading
import ctypes
from PIL import Image, ImageTk
import cairosvg
from werkzeug.serving import make_server
from pystray import Icon, Menu, MenuItem
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from database.db_utils import add_permission, add_script_parameter, delete_destination, delete_script_parameter, edit_origin, edit_script, edit_script_parameter, get_all_users, get_destinations_by_user, get_all_scripts, add_script, delete_script, get_script_parameters, resource_path, get_all_destinations, add_destination, get_destination_by_id, update_destination, update_origin, update_permission, update_script, update_script_parameter, update_user_destinations, delete_permission, get_all_permissions, get_all_origins, add_origin, delete_origin, get_all_users
from web.monitor import app

LOG_FILE = resource_path("logs/controlador.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),    
        logging.StreamHandler(sys.stdout)
    ]
)

sys.path.append(resource_path(''))

class MonitorControllerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Controlador do Monitor")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # Configurar o tema do customtkinter
        ctk.set_appearance_mode("dark")  # Tema escuro
        ctk.set_default_color_theme("dark-blue")  # Paleta de cores

        # Centralizar a janela
        self.center_window()

        # Adicionar o ícone SVG à aplicação
        try:
            icon_path = resource_path("web/static/img/icone.svg")
            icon_image = self.convert_svg_to_photoimage(icon_path)
            self.root.iconphoto(True, icon_image)
            app_id = 'py.etl.monitor.controlador'  # Identificador único para o aplicativo
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception as e:
            logging.error(f"Erro ao carregar o ícone SVG: {e}")

        self.server_thread = None
        self.server_running = False
        self.http_server = None  # Referência ao servidor HTTP

        # Frame principal
        main_frame = ctk.CTkFrame(root, corner_radius=10)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Botões de controle
        button_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        button_frame.pack(pady=10)

        self.start_button = ctk.CTkButton(
            button_frame, text="Iniciar Servidor", command=self.start_server, width=150,
            fg_color="#BDBDBD",  # Cinza claro
            hover_color="#81C784",  # Verde suave no hover
            text_color="white"
        )
        self.start_button.grid(row=0, column=0, padx=10)

        self.stop_button = ctk.CTkButton(
            button_frame, text="Parar Servidor", command=self.stop_server, width=150,
            fg_color="#BDBDBD",  # Cinza claro
            hover_color="#E57373",  # Vermelho suave no hover
            text_color="white", state="disabled"
        )
        self.stop_button.grid(row=0, column=1, padx=10)

        self.open_browser_button = ctk.CTkButton(
            button_frame, text="Abrir no Navegador", command=self.open_browser, width=150,
            fg_color="#BDBDBD",  # Cinza claro
            hover_color="#64B5F6",  # Azul suave no hover
            text_color="white"
        )
        self.open_browser_button.grid(row=1, column=0, columnspan=2, pady=10)

        # Área de logs
        log_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        log_label = ctk.CTkLabel(log_frame, text="Logs do Servidor", anchor="w", text_color="#B0BEC5")
        log_label.pack(fill=tk.X, padx=10, pady=5)

        self.log_text = tk.Text(
            log_frame, height=10, state=tk.DISABLED, wrap=tk.WORD,
            bg="#424242", fg="#E0E0E0"
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        log_scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scrollbar.set)

        # Botão para limpar logs
        clear_log_button = ctk.CTkButton(
            main_frame, text="Limpar Logs", command=self.clear_logs,
            fg_color="#BDBDBD", hover_color="#757575", text_color="black"
        )
        clear_log_button.pack(pady=10)

        # Configurar o evento de fechamento da janela
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Configurar o ícone na bandeja
        self.tray_icon = None
        self.create_tray_icon()

        # Perguntar ao usuário se deseja iniciar o servidor antes de minimizar para a bandeja
        # self.ask_to_start_server()

        # Iniciar o servidor automaticamente
        self.start_server()
        self.minimize_to_tray()

        menu_bar = tk.Menu(self.root)

        # Menu de Gerenciamento
        manage_menu = tk.Menu(menu_bar, tearoff=0)
        manage_menu.add_command(label="Gerenciar Scripts", command=self.open_script_manager)
        manage_menu.add_command(label="Gerenciar Origens", command=self.open_origin_manager)
        manage_menu.add_command(label="Gerenciar Destinos", command=self.open_destination_manager)
        manage_menu.add_command(label="Gerenciar Permissões", command=self.open_permission_manager)
        menu_bar.add_cascade(label="Gerenciamento", menu=manage_menu)

        # Adicionar a barra de menu à janela principal
        self.root.config(menu=menu_bar)

    def center_window(self):
        """Centralizar a janela na tela."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def convert_svg_to_photoimage(self, svg_path):
        """
        Converte um arquivo SVG para um objeto PhotoImage do Tkinter.
        """
        import cairosvg
        import io
        from PIL import Image, ImageTk

        # Converter o SVG para PNG em memória
        png_data = cairosvg.svg2png(url=svg_path)

        # Carregar o PNG em um objeto PIL Image
        image = Image.open(io.BytesIO(png_data))

        # Converter o PIL Image para PhotoImage
        return ImageTk.PhotoImage(image)

    # def ask_to_start_server(self):
    #     """Perguntar ao usuário se deseja iniciar o servidor."""
    #     dialog = ctk.CTkToplevel(self.root)
    #     dialog.title("Confirmação")
    #     dialog.geometry("350x180")  # Aumentar o tamanho da janela
    #     dialog.resizable(False, False)

    #     # Centralizar a janela de diálogo
    #     dialog.update_idletasks()
    #     x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
    #     y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
    #     dialog.geometry(f"+{x}+{y}")

    #     # Configurar o fundo da janela
    #     dialog.configure(bg="#424242")  # Fundo cinza escuro

    #     # Adicionar widgets ao diálogo
    #     label = ctk.CTkLabel(dialog, text="Deseja iniciar o servidor?", anchor="center", text_color="#FFFFFF")
    #     label.pack(pady=20)

    #     button_frame = ctk.CTkFrame(dialog, corner_radius=10)
    #     button_frame.pack(pady=10)

    #     def on_yes():
    #         self.start_server()
    #         dialog.destroy()

    #     def on_no():
    #         dialog.destroy()

    #     yes_button = ctk.CTkButton(
    #         button_frame, text="Sim", command=on_yes,
    #         fg_color="#BDBDBD",  # Cinza claro
    #         hover_color="#81C784",  # Verde suave no hover
    #         text_color="white",
    #         width=100  # Largura fixa para os botões
    #     )
    #     yes_button.grid(row=0, column=0, padx=10, pady=5)

    #     no_button = ctk.CTkButton(
    #         button_frame, text="Não", command=on_no,
    #         fg_color="#BDBDBD",  # Cinza claro
    #         hover_color="#E57373",  # Vermelho suave no hover
    #         text_color="white",
    #         width=100  # Largura fixa para os botões
    #     )
    #     no_button.grid(row=0, column=1, padx=10, pady=5)

    #     dialog.transient(self.root)  # Tornar o diálogo modal
    #     dialog.grab_set()  # Bloquear interações com a janela principal
    #     self.root.wait_window(dialog)  # Esperar o fechamento do diálogo

    def start_server(self):
        if not self.server_running:
            self.server_thread = threading.Thread(target=self.run_server, daemon=True)
            self.server_thread.start()
            self.server_running = True
            self.start_button.configure(state="disabled")  # Alterado para 'configure'
            self.stop_button.configure(state="normal")  # Alterado para 'configure'
            self.log_message("Servidor iniciado.")
            self.create_tray_icon()  # Atualizar o menu do tray icon

    def stop_server(self):
        if self.server_running:
            try:
                self.http_server.shutdown()
                self.log_message("Servidor parado com sucesso.")
            except Exception as e:
                self.log_message(f"Erro ao parar o servidor: {e}")
            finally:
                self.server_running = False
                self.start_button.configure(state="normal")  # Alterado para 'configure'
                self.stop_button.configure(state="disabled")  # Alterado para 'configure'
                self.create_tray_icon()  # Atualizar o menu do tray icon

    def run_server(self):
        try:
            self.http_server = make_server('127.0.0.1', 5000, app)
            self.http_server.serve_forever()
        except Exception as e:
            self.log_message(f"Erro ao iniciar o servidor: {e}")

    def open_browser(self):
        if self.server_running:
            import webbrowser
            webbrowser.open("http://127.0.0.1:5000")
        else:
            self.log_message("O servidor não está em execução. Inicie o servidor antes de abrir o navegador.")

    def log_message(self, message):
        """Exibir uma mensagem na área de logs."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

    def clear_logs(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def on_close(self):
        if self.server_running:
            # Criar uma janela de diálogo personalizada
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Confirmação")
            dialog.geometry("350x180")  # Aumentar o tamanho da janela
            dialog.resizable(False, False)

            # Centralizar a janela de diálogo
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")

            # Adicionar widgets ao diálogo
            label = ctk.CTkLabel(dialog, text="O servidor está em execução.\nDeseja interromper a execução?", anchor="center", text_color="#FFFFFF")
            label.pack(pady=20)

            button_frame = ctk.CTkFrame(dialog, corner_radius=10)
            button_frame.pack(pady=10)

            def on_yes():
                self.exit_application()
                dialog.destroy()

            def on_no():
                dialog.destroy()
                self.minimize_to_tray()

            yes_button = ctk.CTkButton(
                button_frame, text="Sim", command=on_yes,
                fg_color="#BDBDBD",  # Cinza claro
                hover_color="#81C784",  # Verde suave no hover
                text_color="white",
                width=100  # Largura fixa para os botões
            )
            yes_button.grid(row=0, column=0, padx=10, pady=5)

            no_button = ctk.CTkButton(
                button_frame, text="Não", command=on_no,
                fg_color="#BDBDBD",  # Cinza claro
                hover_color="#E57373",  # Vermelho suave no hover
                text_color="white",
                width=100  # Largura fixa para os botões
            )
            no_button.grid(row=0, column=1, padx=10, pady=5)

            dialog.transient(self.root)  # Tornar o diálogo modal
            dialog.grab_set()  # Bloquear interações com a janela principal
            self.root.wait_window(dialog)  # Esperar o fechamento do diálogo
        else:
            self.exit_application()  # Encerrar a aplicação diretamente se o servidor não estiver em execução

    def minimize_to_tray(self):
        self.root.withdraw()  # Ocultar a janela principal
        self.tray_icon.visible = True  # Tornar o ícone visível
        self.create_tray_icon()  # Atualizar o menu do tray icon

    def create_tray_icon(self):
        """
        Cria o ícone da bandeja do sistema e aplica o ícone à janela principal.
        """
        try:
            # Caminho para o arquivo SVG
            svg_path = resource_path("web/static/img/icone.svg")

            # Converter o SVG para PNG em memória
            png_path = resource_path("web/static/img/icone.png")
            cairosvg.svg2png(url=svg_path, write_to=png_path)

            # Salvar o PNG como ICO em um arquivo temporário
            ico_path = resource_path("web/static/img/icone.ico")
            image = Image.open(png_path)
            image.save(ico_path, format="ICO")

            # Aplicar o ícone à janela principal usando o arquivo PNG
            self.root.iconphoto(True, ImageTk.PhotoImage(file=png_path))

            # Criar o menu do tray icon dinamicamente
            def get_menu():
                return Menu(
                    MenuItem(
                        "Minimizar Controlador" if self.root.state() == "normal" else "Abrir Controlador",
                        self.toggle_window
                    ),
                    MenuItem("Iniciar Servidor", self.start_server, enabled=not self.server_running),
                    MenuItem("Parar Servidor", self.stop_server, enabled=self.server_running),
                    MenuItem("Abrir no Navegador", self.open_browser),
                    MenuItem("Fechar Controlador", self.exit_application)
                )

            # Criar o ícone na bandeja
            if self.tray_icon is None:  # Criar o ícone apenas se ele ainda não existir
                self.tray_icon = Icon(
                    "Controlador",
                    Image.open(ico_path),  # Passar o objeto de imagem ICO
                    "Controlador do Monitor",
                    menu=get_menu()
                )

                # Configurar o menu e iniciar o ícone
                self.tray_icon.menu = get_menu()
                self.tray_icon.run_detached()
            else:
                self.tray_icon.menu = get_menu()  # Atualizar o menu do ícone
        except Exception as e:
            logging.error(f"Erro ao criar o ícone da bandeja: {e}")

    def toggle_window(self):
        """Alternar a visibilidade da janela principal."""
        def toggle():
            if self.root.state() == "normal":
                self.root.withdraw()
            else:
                self.root.deiconify()

        # Garantir que a execução ocorra no thread principal
        try:
            self.root.after(0, toggle)
        except RuntimeError:
            pass  # Ignora se não estiver no mainloop

    def show_window(self):
        self.root.deiconify()  # Reexibir a janela principal
        self.tray_icon.visible = False  # Ocultar o ícone na bandeja

    def exit_application(self):
        if self.server_running:
            self.stop_server()  # Parar o servidor, se estiver em execução
        if self.tray_icon:
            self.tray_icon.visible = False  # Ocultar o ícone na bandeja
            self.tray_icon.stop()  # Parar o loop do ícone na bandeja
        try:
            self.root.after(0, self.root.destroy)  # Garantir que destroy seja chamado no thread principal
        except RuntimeError:
            pass  # Ignorar erros se o loop principal já foi encerrado
        finally:
            os._exit(0)  # Forçar o encerramento completo do processo

    def open_script_manager(self):
        """Abrir a janela de gerenciamento de scripts."""
        script_window = ctk.CTkToplevel(self.root)
        script_window.title("Gerenciar Scripts")
        script_window.geometry("900x600")

        # Variáveis para armazenar o estado atual
        current_script_id = tk.IntVar(value=0)

        # --- Parte Superior ---
        top_frame = ctk.CTkFrame(script_window)
        top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Esquerda Superior: Formulário de Script ---
        form_frame = ctk.CTkFrame(top_frame, width=450)
        form_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        name_label = ctk.CTkLabel(form_frame, text="Nome:")
        name_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        name_entry = ctk.CTkEntry(form_frame)
        name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        content_label = ctk.CTkLabel(form_frame, text="Conteúdo:")
        content_label.grid(row=1, column=0, padx=5, pady=5, sticky="nw")
        content_text = tk.Text(form_frame, height=10, wrap=tk.WORD)
        content_text.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Botões de ação para o script
        button_frame = ctk.CTkFrame(form_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        def save_script():
            """Salvar ou atualizar o script."""
            name = name_entry.get().strip()
            content = content_text.get("1.0", tk.END).strip()

            if not name or not content:
                self.log_message("Erro: Nome e conteúdo são obrigatórios!")
                return

            try:
                if current_script_id.get() == 0:  # Novo script
                    add_script(name, content)
                    self.log_message(f"Script '{name}' adicionado com sucesso!")
                else:  # Atualizar script existente
                    update_script(current_script_id.get(), name, content)
                    self.log_message(f"Script '{name}' atualizado com sucesso!")
                refresh_scripts()
                clear_form()
            except Exception as e:
                self.log_message(f"Erro ao salvar script: {e}")

        def clear_form():
            """Limpar o formulário."""
            current_script_id.set(0)
            name_entry.delete(0, tk.END)
            content_text.delete("1.0", tk.END)
            refresh_parameters()

        save_button = ctk.CTkButton(button_frame, text="Salvar", command=save_script)
        save_button.grid(row=0, column=0, padx=5)

        new_button = ctk.CTkButton(button_frame, text="Novo", command=clear_form)
        new_button.grid(row=0, column=1, padx=5)

        # --- Direita Superior: Lista de Parâmetros ---
        parameter_frame = ctk.CTkFrame(top_frame, width=450)
        parameter_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        parameter_list = ctk.CTkFrame(parameter_frame)
        parameter_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        def refresh_parameters():
            """Atualizar a lista de parâmetros do script selecionado."""
            for widget in parameter_list.winfo_children():
                widget.destroy()

            if current_script_id.get() == 0:
                return  # Nenhum script selecionado

            parameters = get_script_parameters(current_script_id.get())
            for param_id, name, value in parameters:
                frame = ctk.CTkFrame(parameter_list)
                frame.pack(fill=tk.X, pady=5)
                
                name_entry = ctk.CTkEntry(frame, width=120)
                name_entry.insert(0, name)
                name_entry.pack(side=tk.LEFT, padx=10)

                value_entry = ctk.CTkEntry(frame)
                value_entry.insert(0, value)
                value_entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

                # Use default arguments in lambda to capture current values
                save_button = ctk.CTkButton(
                    frame, text="Salvar",
                    command=lambda pid=param_id, n=name_entry, v=value_entry: save_parameter(pid, n, v)
                )
                save_button.pack(side=tk.RIGHT, padx=5)

                delete_button = ctk.CTkButton(
                    frame, text="Excluir",
                    command=lambda pid=param_id: delete_param(pid)
                )
                delete_button.pack(side=tk.RIGHT, padx=5)

        def save_parameter(param_id, name_entry, value_entry):
            new_name = name_entry.get().strip()
            new_value = value_entry.get().strip()
            if not new_name:
                self.log_message("Erro: O nome do parâmetro não pode ser vazio!")
                return
            try:
                update_script_parameter(param_id, new_name, new_value)
                self.log_message(f"Parâmetro '{new_name}' atualizado com sucesso!")
                refresh_parameters()
            except Exception as e:
                self.log_message(f"Erro ao atualizar parâmetro '{new_name}': {e}")

        def delete_param(param_id):
            try:
                delete_script_parameter(param_id)
                self.log_message("Parâmetro excluído com sucesso!")
                refresh_parameters()
            except Exception as e:
                self.log_message(f"Erro ao excluir parâmetro: {e}")

        def add_parameter():
            """Adicionar um novo parâmetro ao script."""
            if current_script_id.get() == 0:
                self.log_message("Erro: Salve o script antes de adicionar parâmetros!")
                return

            try:
                add_script_parameter(current_script_id.get(), "novo_parametro", "")
                self.log_message("Novo parâmetro adicionado com sucesso!")
                refresh_parameters()
            except Exception as e:
                self.log_message(f"Erro ao adicionar parâmetro: {e}")

        # Botão para adicionar novo parâmetro
        add_parameter_button = ctk.CTkButton(parameter_frame, text="Adicionar Parâmetro", command=add_parameter)
        add_parameter_button.pack(pady=10)

        # --- Parte Inferior: Lista de Scripts ---
        script_list_frame = ctk.CTkFrame(script_window)
        script_list_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, padx=10, pady=10, expand=True)

        def refresh_scripts():
            """Atualizar a lista de scripts."""
            for widget in script_list_frame.winfo_children():
                widget.destroy()

            scripts = get_all_scripts()
            for script_id, name, content in scripts:
                frame = ctk.CTkFrame(script_list_frame)
                frame.pack(fill=tk.X, pady=5)

                label_name = ctk.CTkLabel(frame, text=name)
                label_name.pack(side=tk.LEFT, padx=10)

                edit_button = ctk.CTkButton(frame, text="Editar", command=lambda sid=script_id: load_script(sid))
                edit_button.pack(side=tk.RIGHT, padx=5)

                copy_button = ctk.CTkButton(frame, text="Copiar", command=lambda sid=script_id: copy_script(sid))
                copy_button.pack(side=tk.RIGHT, padx=5)

                delete_button = ctk.CTkButton(frame, text="Excluir", command=lambda sid=script_id: del_script(sid))
                delete_button.pack(side=tk.RIGHT, padx=5)

        def load_script(script_id):
            """Carregar os dados de um script para o formulário."""
            script = edit_script(script_id)
            if script:
                current_script_id.set(script["id"])
                name_entry.delete(0, tk.END)
                name_entry.insert(0, script["name"])
                content_text.delete("1.0", tk.END)
                content_text.insert("1.0", script["content"])
                refresh_parameters()

        def copy_script(script_id):
            """Copiar um script existente."""
            script = edit_script(script_id)
            if script:
                new_name = f"{script['name']} (Cópia)"
                add_script(new_name, script["content"])
                self.log_message(f"Script '{new_name}' copiado com sucesso!")
                refresh_scripts()

        def del_script(script_id):
            """Excluir um script."""
            try:
                delete_script(script_id)
                self.log_message("Script excluído com sucesso!")
                refresh_scripts()
            except Exception as e:
                self.log_message(f"Erro ao excluir script: {e}")
        
        #atualizar a lista de scripts ao abrir a janela
        refresh_scripts()

    def open_destination_manager(self):
        """Abrir a janela de gerenciamento de destinos."""
        destination_window = ctk.CTkToplevel(self.root)
        destination_window.title("Gerenciar Destinos")
        destination_window.geometry("600x400")

        # Lista de destinos
        destination_list = ctk.CTkFrame(destination_window)
        destination_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def refresh_destinations():
            """Atualizar a lista de destinos."""
            for widget in destination_list.winfo_children():
                widget.destroy()

            destinations = get_all_destinations()
            for dest_id, name in destinations:
                frame = ctk.CTkFrame(destination_list)
                frame.pack(fill=tk.X, pady=5)

                label_name = ctk.CTkLabel(frame, text=name, width=20)
                label_name.pack(side=tk.LEFT, padx=10)

                edit_button = ctk.CTkButton(frame, text="Editar", command=lambda did=dest_id: edit_destination(did))
                edit_button.pack(side=tk.RIGHT, padx=5)

                delete_button = ctk.CTkButton(frame, text="Excluir", command=lambda did=dest_id: delete_destination_action(did))
                delete_button.pack(side=tk.RIGHT, padx=5)

        def add_destination_action():
            name = name_entry.get().strip()
            description = description_entry.get().strip()
            project_id = project_id_entry.get().strip()
            dataset_id = dataset_id_entry.get().strip()
            table_id = table_id_entry.get().strip()
            keyfile = keyfile_entry.get().strip()

            if not name:
                self.log_message("Erro: O nome do destino é obrigatório!")
                return

            try:
                add_destination(name, description, project_id, dataset_id, table_id, keyfile)
                self.log_message(f"Destino '{name}' adicionado com sucesso!")
                refresh_destinations()
                # Limpar campos após salvar
                name_entry.delete(0, tk.END)
                description_entry.delete(0, tk.END)
                project_id_entry.delete(0, tk.END)
                dataset_id_entry.delete(0, tk.END)
                table_id_entry.delete(0, tk.END)
                keyfile_entry.delete(0, tk.END)
            except Exception as e:
                self.log_message(f"Erro ao adicionar destino '{name}': {e}")

        def edit_destination(dest_id):
            destination = get_destination_by_id(dest_id)
            if destination:
                name_entry.delete(0, tk.END)
                name_entry.insert(0, destination[1])
                description_entry.delete(0, tk.END)
                description_entry.insert(0, destination[2])
                project_id_entry.delete(0, tk.END)
                project_id_entry.insert(0, destination[3] or "")
                dataset_id_entry.delete(0, tk.END)
                dataset_id_entry.insert(0, destination[4] or "")
                table_id_entry.delete(0, tk.END)
                table_id_entry.insert(0, destination[5] or "")
                keyfile_entry.delete(0, tk.END)
                keyfile_entry.insert(0, destination[6])

                def save_changes():
                    name = name_entry.get().strip()
                    description = description_entry.get().strip()
                    project_id = project_id_entry.get().strip()
                    dataset_id = dataset_id_entry.get().strip()
                    table_id = table_id_entry.get().strip()
                    keyfile = keyfile_entry.get().strip()

                    if not name:
                        self.log_message("Erro: O nome do destino é obrigatório!")
                        return

                    try:
                        update_destination(dest_id, name, description, project_id, dataset_id, table_id, keyfile)
                        self.log_message(f"Destino '{name}' atualizado com sucesso!")
                        refresh_destinations()
                        # Limpar campos após salvar
                        name_entry.delete(0, tk.END)
                        description_entry.delete(0, tk.END)
                        project_id_entry.delete(0, tk.END)
                        dataset_id_entry.delete(0, tk.END)
                        table_id_entry.delete(0, tk.END)
                        keyfile_entry.delete(0, tk.END)
                    except Exception as e:
                        self.log_message(f"Erro ao atualizar destino '{name}': {e}")

                save_button.configure(command=save_changes)

        def delete_destination_action(dest_id):
            """Excluir um destino."""
            try:
                delete_destination(dest_id)
                self.log_message(f"Destino excluído com sucesso!")
                refresh_destinations()
            except Exception as e:
                self.log_message(f"Erro ao excluir destino: {e}")

        # Formulário para adicionar/editar destinos
        form_frame = ctk.CTkFrame(destination_window)
        form_frame.pack(fill=tk.X, padx=10, pady=10)

        form_frame.columnconfigure(1, weight=1)  # Faz a segunda coluna expandir

        name_label = ctk.CTkLabel(form_frame, text="Nome:")
        name_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        name_entry = ctk.CTkEntry(form_frame)
        name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        description_label = ctk.CTkLabel(form_frame, text="Descrição:")
        description_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        description_entry = ctk.CTkEntry(form_frame)
        description_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        project_id_label = ctk.CTkLabel(form_frame, text="Project ID:")
        project_id_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        project_id_entry = ctk.CTkEntry(form_frame)
        project_id_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        dataset_id_label = ctk.CTkLabel(form_frame, text="Dataset ID:")
        dataset_id_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        dataset_id_entry = ctk.CTkEntry(form_frame)
        dataset_id_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        
        table_id_label = ctk.CTkLabel(form_frame, text="Table ID:")
        table_id_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        table_id_entry = ctk.CTkEntry(form_frame)
        table_id_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        keyfile_label = ctk.CTkLabel(form_frame, text="Arquivo JSON:")
        keyfile_label.grid(row=5, column=0, padx=5, pady=5, sticky="w")
        keyfile_entry = ctk.CTkEntry(form_frame)
        keyfile_entry.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

        save_button = ctk.CTkButton(form_frame, text="Salvar", command=add_destination_action)
        save_button.grid(row=6, column=0, columnspan=2, pady=10, sticky="ew")

        refresh_destinations()

    def open_user_destination_manager(self):
        """Abrir a janela de gerenciamento de destinos por usuário."""
        manager_window = ctk.CTkToplevel(self.root)
        manager_window.title("Vincular Destinos aos Usuários")
        manager_window.geometry("600x400")

        # Lista de usuários
        user_list_frame = ctk.CTkFrame(manager_window)
        user_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def refresh_user_destinations():
            """Atualizar a lista de usuários e seus destinos."""
            for widget in user_list_frame.winfo_children():
                widget.destroy()

            users = get_all_users()
            for user_id, username in users:
                frame = ctk.CTkFrame(user_list_frame)
                frame.pack(fill=tk.X, pady=5)

                label_username = ctk.CTkLabel(frame, text=username, width=20)
                label_username.pack(side=tk.LEFT, padx=10)

                edit_button = ctk.CTkButton(frame, text="Vincular Destinos", command=lambda uid=user_id: edit_user_destinations(uid))
                edit_button.pack(side=tk.RIGHT, padx=5)

        def edit_user_destinations(user_id):
            """Editar os destinos vinculados a um usuário."""
            user_destinations = get_destinations_by_user(user_id)
            all_destinations = get_all_destinations()

            # Janela para editar destinos
            edit_window = ctk.CTkToplevel(manager_window)
            edit_window.title(f"Vincular Destinos ao Usuário {user_id}")
            edit_window.geometry("400x400")

            # Lista para armazenar os checkboxes
            checkboxes = []

            # Exibir uma lista de destinos com checkboxes
            for dest_id, dest_name in all_destinations:
                is_checked = dest_id in user_destinations
                var = tk.BooleanVar(value=is_checked)
                checkbox = ctk.CTkCheckBox(edit_window, text=dest_name, variable=var)
                checkbox.pack(anchor="w", padx=10, pady=5)
                checkboxes.append((dest_id, var))  # Armazenar o ID do destino e a variável associada

            def save_changes():
                """Salvar as alterações de destinos vinculados ao usuário."""
                selected_destinations = [dest_id for dest_id, var in checkboxes if var.get()]
                try:
                    update_user_destinations(user_id, selected_destinations)
                    self.log_message(f"Destinos vinculados ao usuário {user_id} atualizados com sucesso!")
                    edit_window.destroy()  # Fechar a janela após salvar
                    refresh_user_destinations()  # Atualizar a lista de usuários e destinos
                except Exception as e:
                    self.log_message(f"Erro ao atualizar destinos do usuário {user_id}: {e}")

            # Botão para salvar as alterações
            save_button = ctk.CTkButton(edit_window, text="Salvar Alterações", command=save_changes)
            save_button.pack(pady=10)

        refresh_user_destinations()

    def open_origin_manager(self):
        """Abrir a janela de gerenciamento de origens."""
        origin_window = ctk.CTkToplevel(self.root)
        origin_window.title("Gerenciar Origens")
        origin_window.geometry("600x500")

        # Lista de origens
        origin_list = ctk.CTkFrame(origin_window)
        origin_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def refresh_origins():
            """Atualizar a lista de origens."""
            for widget in origin_list.winfo_children():
                widget.destroy()

            origins = get_all_origins()  # Função que retorna todas as origens
            for origin_id, name in origins:
                frame = ctk.CTkFrame(origin_list)
                frame.pack(fill=tk.X, pady=5)

                label_name = ctk.CTkLabel(frame, text=name, width=20)
                label_name.pack(side=tk.LEFT, padx=10)

                edit_button = ctk.CTkButton(frame, text="Editar", command=lambda oid=origin_id: edit_origin_action(oid))
                edit_button.pack(side=tk.RIGHT, padx=5)

                delete_button = ctk.CTkButton(frame, text="Excluir", command=lambda oid=origin_id: delete_origin_action(oid))
                delete_button.pack(side=tk.RIGHT, padx=5)

        def add_origin_action():
            name = name_entry.get().strip()
            dsn = dsn_entry.get().strip()
            user = user_entry.get().strip()
            password = password_entry.get().strip()

            if not name or not dsn:
                self.log_message("Erro: Nome e DSN são obrigatórios!")
                return

            try:
                if getattr(form_frame, "origin_editing_id", None) is not None:
                    # Atualizar origem existente
                    update_origin(form_frame.origin_editing_id, name, dsn, user, password)
                    self.log_message(f"Origem '{name}' atualizada com sucesso!")
                    form_frame.origin_editing_id = None
                else:
                    # Adicionar nova origem
                    add_origin(name, dsn, user, password)
                    self.log_message(f"Origem '{name}' adicionada com sucesso!")
                refresh_origins()
                # Limpar campos após salvar
                name_entry.delete(0, tk.END)
                dsn_entry.delete(0, tk.END)
                user_entry.delete(0, tk.END)
                password_entry.delete(0, tk.END)
            except Exception as e:
                self.log_message(f"Erro ao salvar origem '{name}': {e}")

        def edit_origin_action(origin_id):
            """Carregar os dados da origem para edição."""
            try:
                origin = edit_origin(origin_id)
                name_entry.delete(0, tk.END)
                name_entry.insert(0, origin["name"])
                dsn_entry.delete(0, tk.END)
                dsn_entry.insert(0, origin["dsn"])
                user_entry.delete(0, tk.END)
                user_entry.insert(0, origin["user"])
                password_entry.delete(0, tk.END)
                password_entry.insert(0, origin["password"])
                # Armazene o ID da origem em edição (adicione uma variável para isso)
                form_frame.origin_editing_id = origin_id
            except Exception as e:
                self.log_message(f"Erro ao carregar origem para edição: {e}")

        def delete_origin_action(origin_id):
            """Excluir uma origem."""
            try:
                delete_origin(origin_id)
                self.log_message("Origem excluída com sucesso!")
                refresh_origins()
            except Exception as e:
                self.log_message(f"Erro ao excluir origem: {e}")

        # Formulário para adicionar/editar origens
        form_frame = ctk.CTkFrame(origin_window)
        form_frame.origin_editing_id = None  # Para saber se está editando ou criando
        form_frame.pack(fill=tk.X, padx=10, pady=10)

        form_frame.columnconfigure(1, weight=1)  # Faz a segunda coluna expandir

        name_label = ctk.CTkLabel(form_frame, text="Nome:")
        name_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        name_entry = ctk.CTkEntry(form_frame)
        name_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        dsn_label = ctk.CTkLabel(form_frame, text="DSN:")
        dsn_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        dsn_entry = ctk.CTkEntry(form_frame)
        dsn_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        user_label = ctk.CTkLabel(form_frame, text="Usuário:")
        user_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        user_entry = ctk.CTkEntry(form_frame)
        user_entry.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        password_label = ctk.CTkLabel(form_frame, text="Senha:")
        password_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        password_entry = ctk.CTkEntry(form_frame, show="*")
        password_entry.grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        save_button = ctk.CTkButton(form_frame, text="Salvar", command=add_origin_action)
        save_button.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")

        refresh_origins()

    def open_permission_manager(self):
        """Abrir a janela de gerenciamento de permissões."""
        permission_window = ctk.CTkToplevel(self.root)
        permission_window.title("Gerenciar Permissões")
        permission_window.geometry("950x400")
        permission_editing_id = [None]  # Use lista para mutabilidade em closures

        # Frames para os grids
        frame_usuarios = ctk.CTkFrame(permission_window)
        frame_usuarios.grid(row=0, column=0, padx=5, pady=5, sticky="ns")
        frame_origens = ctk.CTkFrame(permission_window)
        frame_origens.grid(row=0, column=1, padx=5, pady=5, sticky="ns")
        frame_destinos = ctk.CTkFrame(permission_window)
        frame_destinos.grid(row=0, column=2, padx=5, pady=5, sticky="ns")
        frame_scripts = ctk.CTkFrame(permission_window)
        frame_scripts.grid(row=0, column=3, padx=5, pady=5, sticky="ns")
        frame_permissoes = ctk.CTkFrame(permission_window)
        frame_permissoes.grid(row=0, column=4, padx=5, pady=5, sticky="ns")

        # --- Usuários ---
        ctk.CTkLabel(frame_usuarios, text="Usuários").pack()
        usuarios = get_all_users()
        usuario_vars = {}
        for uid, uname in usuarios:
            var = tk.BooleanVar()
            chk = ctk.CTkCheckBox(frame_usuarios, text=uname, variable=var)
            chk.pack(anchor="w", padx=5, pady=2)
            usuario_vars[uid] = var

        # --- Origens ---
        ctk.CTkLabel(frame_origens, text="Origens").pack()
        origens = get_all_origins()
        origem_vars = {}
        for oid, oname in origens:
            var = tk.BooleanVar()
            chk = ctk.CTkCheckBox(frame_origens, text=oname, variable=var)
            chk.pack(anchor="w", padx=5, pady=2)
            origem_vars[oid] = var

        # --- Destinos ---
        ctk.CTkLabel(frame_destinos, text="Destinos").pack()
        destinos = get_all_destinations()
        destino_vars = {}
        for did, dname in destinos:
            var = tk.BooleanVar()
            chk = ctk.CTkCheckBox(frame_destinos, text=dname, variable=var)
            chk.pack(anchor="w", padx=5, pady=2)
            destino_vars[did] = var

        # --- Scripts ---
        ctk.CTkLabel(frame_scripts, text="Scripts").pack()
        scripts = get_all_scripts()
        script_vars = {}
        for sid, sname, _ in scripts:
            var = tk.BooleanVar()
            chk = ctk.CTkCheckBox(frame_scripts, text=sname, variable=var)
            chk.pack(anchor="w", padx=5, pady=2)
            script_vars[sid] = var

        # --- Permissões já salvas ---
        def refresh_permissoes():
            for widget in frame_permissoes.winfo_children():
                widget.destroy()
            ctk.CTkLabel(frame_permissoes, text="Permissões Salvas").pack()
            permissoes = get_all_permissions()
            for perm in permissoes:
                text = f"Usuário: {perm['user_id']} | Origem: {perm['origin_id']} | Script: {perm['script_id']} | Destino: {perm['destination_id']}"
                row = ctk.CTkFrame(frame_permissoes)
                row.pack(fill=tk.X, pady=2)
                ctk.CTkLabel(row, text=text).pack(side=tk.LEFT, padx=5)
                btn_excluir = ctk.CTkButton(row, text="Excluir", width=60, command=lambda pid=perm['id']: delete_permission_action(pid))
                btn_excluir.pack(side=tk.RIGHT, padx=5)
                btn_editar = ctk.CTkButton(row, text="Editar", width=60, command=lambda p=perm: editar_permissao_action(p))
                btn_editar.pack(side=tk.RIGHT, padx=5)

        def delete_permission_action(perm_id):
            try:
                delete_permission(perm_id)
                self.log_message("Permissão excluída com sucesso!")
                refresh_permissoes()
            except Exception as e:
                self.log_message(f"Erro ao excluir permissão: {e}")

        def editar_permissao_action(perm):
            permission_editing_id[0] = perm['id']
            for uid, var in usuario_vars.items():
                var.set(uid == perm['user_id'])
            for oid, var in origem_vars.items():
                var.set(oid == perm['origin_id'])
            for did, var in destino_vars.items():
                var.set(did == perm['destination_id'])
            for sid, var in script_vars.items():
                var.set(sid == perm['script_id'])
            self.log_message("Permissão carregada para edição. Altere e clique em Salvar Permissão.")

        refresh_permissoes()

        # --- Botão para salvar nova permissão ---
        def salvar_permissao():
            usuarios_sel = [uid for uid, var in usuario_vars.items() if var.get()]
            origens_sel = [oid for oid, var in origem_vars.items() if var.get()]
            destinos_sel = [did for did, var in destino_vars.items() if var.get()]
            scripts_sel = [sid for sid, var in script_vars.items() if var.get()]

            if not usuarios_sel or not origens_sel or not destinos_sel or not scripts_sel:
                self.log_message("Selecione pelo menos um de cada categoria para criar permissão.")
                return

            try:
                if permission_editing_id[0] is not None:
                    # Atualizar permissão existente (pegue o primeiro selecionado de cada)
                    update_permission(
                        permission_editing_id[0],
                        usuarios_sel[0],
                        origens_sel[0],
                        scripts_sel[0],
                        destinos_sel[0]
                    )
                    self.log_message("Permissão atualizada com sucesso!")
                    permission_editing_id[0] = None
                else:
                    # Criar novas permissões
                    for uid in usuarios_sel:
                        for oid in origens_sel:
                            for did in destinos_sel:
                                for sid in scripts_sel:
                                    add_permission(uid, oid, sid, did)
                self.log_message("Permissões adicionadas com sucesso!")
                refresh_permissoes()     
                           
                for var in usuario_vars.values():
                    var.set(False)
                for var in origem_vars.values():
                    var.set(False)
                for var in destino_vars.values():
                    var.set(False)
                for var in script_vars.values():
                    var.set(False)
            except Exception as e:
                self.log_message(f"Erro ao adicionar/atualizar permissão: {e}")

        btn_salvar = ctk.CTkButton(permission_window, text="Salvar Permissão", command=salvar_permissao)
        btn_salvar.grid(row=1, column=0, columnspan=5, pady=10, sticky="ew")

    def open_script_parameter_manager(self, script_id):
        """Abrir a janela de gerenciamento de parâmetros de um script."""
        parameter_window = ctk.CTkToplevel(self.root)
        parameter_window.title(f"Gerenciar Parâmetros do Script {script_id}")
        parameter_window.geometry("600x400")

        # Lista de parâmetros
        parameter_list = ctk.CTkFrame(parameter_window)
        parameter_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def refresh_parameters():
            """Atualizar a lista de parâmetros."""
            for widget in parameter_list.winfo_children():
                widget.destroy()

            parameters = get_script_parameters(script_id)
            for param_id, name, value in parameters:
                frame = ctk.CTkFrame(parameter_list)
                frame.pack(fill=tk.X, pady=5)

                label_name = ctk.CTkLabel(frame, text=f"{name}: {value}", width=20)
                label_name.pack(side=tk.LEFT, padx=10)

                edit_button = ctk.CTkButton(frame, text="Editar", command=lambda pid=param_id: edit_script_parameter(pid))
                edit_button.pack(side=tk.RIGHT, padx=5)

                delete_button = ctk.CTkButton(frame, text="Excluir", command=lambda pid=param_id: delete_script_parameter(pid))
                delete_button.pack(side=tk.RIGHT, padx=5)

        def add_parameter_action():
            """Adicionar um novo parâmetro."""
            name = name_entry.get().strip()
            value = value_entry.get().strip()

            if not name:
                self.log_message("Erro: O nome do parâmetro é obrigatório!")
                return

            try:
                add_script_parameter(script_id, name, value)
                self.log_message(f"Parâmetro '{name}' adicionado com sucesso!")
                refresh_parameters()
                # Limpar campos após salvar
                name_entry.delete(0, tk.END)
                value_entry.delete(0, tk.END)
            except Exception as e:
                self.log_message(f"Erro ao adicionar parâmetro '{name}': {e}")

        # Formulário para adicionar/editar parâmetros
        form_frame = ctk.CTkFrame(parameter_window)
        form_frame.pack(fill=tk.X, padx=10, pady=10)

        name_label = ctk.CTkLabel(form_frame, text="Nome:")
        name_label.grid(row=0, column=0, padx=5, pady=5)
        name_entry = ctk.CTkEntry(form_frame)
        name_entry.grid(row=0, column=1, padx=5, pady=5)

        value_label = ctk.CTkLabel(form_frame, text="Valor:")
        value_label.grid(row=1, column=0, padx=5, pady=5)
        value_entry = ctk.CTkEntry(form_frame)
        value_entry.grid(row=1, column=1, padx=5, pady=5)

        save_button = ctk.CTkButton(form_frame, text="Salvar", command=add_parameter_action)
        save_button.grid(row=2, column=0, columnspan=2, pady=10)

        refresh_parameters()

# Inicializar a interface gráfica
if __name__ == "__main__":
    root = ctk.CTk()
    gui = MonitorControllerApp(root)
    root.mainloop()