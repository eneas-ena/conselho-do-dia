"""
Conselho do Dia — publica 1 Story por dia no Instagram, em ciclo de 60 dias.
Versão 2.0 (API do Instagram com login do Instagram)

Não é preciso editar nada aqui. A chave fica guardada nos "Secrets" do GitHub:
  IG_TOKEN -> token gerado no painel da Meta (Instagram > Configuração da API com login do Instagram)

O token vale 60 dias. Todo domingo este programa o renova sozinho
e o workflow grava o token novo de volta no Secret.
"""
import datetime, json, os, sys, time, urllib.parse, urllib.request

# ---------------- CONFIGURAÇÃO ----------------
DATA_INICIO = datetime.date(2026, 10, 28)   # dia em que sai o "Dia 1" (ajustado quando entrar no ar)
TOTAL_DIAS = 60
URL_IMAGENS = "https://eneas-ena.github.io/conselho-do-dia/stories"
API = "https://graph.instagram.com/v26.0"
FUSO = datetime.timezone(datetime.timedelta(hours=-3))  # horário de Fortaleza
# ----------------------------------------------

TOKEN = os.environ["IG_TOKEN"].strip()


def chamar(metodo, caminho, base=API, **params):
    params["access_token"] = TOKEN
    dados = urllib.parse.urlencode(params)
    url = f"{base}/{caminho}"
    if metodo == "GET":
        req = urllib.request.Request(url + "?" + dados)
    else:
        req = urllib.request.Request(url, data=dados.encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print("ERRO da Meta:", e.read().decode())
        raise


def dia_do_ciclo(hoje):
    return (hoje - DATA_INICIO).days % TOTAL_DIAS + 1


def renovar_token():
    """Renova o token por mais 60 dias e o salva para o workflow atualizar o Secret."""
    try:
        r = chamar("GET", "refresh_access_token", base="https://graph.instagram.com",
                   grant_type="ig_refresh_token")
        with open("novo_token.txt", "w") as f:
            f.write(r["access_token"])
        print(f"Token renovado (vale mais {r.get('expires_in', 0) // 86400} dias).")
    except Exception as e:  # a falha na renovação não impede a publicação
        print("Aviso: não foi possível renovar o token hoje:", e)


def main():
    agora = datetime.datetime.now(FUSO)
    hoje = agora.date()
    dia = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else dia_do_ciclo(hoje)
    imagem = f"{URL_IMAGENS}/conselho-do-dia-{dia:02d}.jpg"

    conta = chamar("GET", "me", fields="user_id,username")
    ig_id = conta["user_id"]
    print(f"Conta @{conta.get('username')} | {hoje} -> Dia {dia}: {imagem}")

    cont = chamar("POST", f"{ig_id}/media", image_url=imagem, media_type="STORIES")
    cid = cont["id"]
    for _ in range(30):  # espera o Instagram processar a imagem (até ~5 min)
        st = chamar("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            break
        if st == "ERROR":
            sys.exit("O Instagram recusou a imagem.")
        time.sleep(10)
    pub = chamar("POST", f"{ig_id}/media_publish", creation_id=cid)
    print("Publicado! id:", pub["id"])

    with open("registro.txt", "a", encoding="utf-8") as f:
        f.write(f"{agora:%Y-%m-%d %H:%M} | Dia {dia:02d} | {pub['id']}\n")

    if agora.weekday() == 6:  # domingo
        renovar_token()


if __name__ == "__main__":
    main()
