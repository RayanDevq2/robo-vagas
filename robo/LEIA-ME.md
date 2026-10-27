# Robô de vagas: passo a passo

## O que cada arquivo faz
- `buscar_vagas.py`: busca vagas (Remotive, RemoteOK, Jobicy), filtra e classifica com IA. Gera `vagas.json`.
- `.github/workflows/vagas.yml`: faz o GitHub rodar o robô todo dia às 8h (Brasília).
- `index.html`: seu painel. A aba "Vagas automáticas" lê o `vagas.json`.

## Montar (uns 15 minutos)
1. Crie uma conta em github.com e um repositório **novo** (pode ser privado para o robô, mas o Pages grátis pede público).
2. Envie os 3 itens acima mantendo as pastas: `index.html`, `buscar_vagas.py` e `.github/workflows/vagas.yml`.
3. **Chave da IA (opcional, melhora o filtro):** no repositório vá em Settings > Secrets and variables > Actions > New repository secret. Nome: `ANTHROPIC_API_KEY`. Valor: sua chave de console.anthropic.com. Sem a chave o robô roda só com o filtro por palavras.
4. Aba **Actions** > "Buscar vagas" > **Run workflow**. Espere terminar (verde). Surge o arquivo `vagas.json`.
5. **Settings > Pages**: Source = branch `main`, pasta `/ (root)`. O endereço do painel aparece ali em alguns minutos.

## Observações
- Fontes: respeite os termos de cada uma. Remotive, RemoteOK e Jobicy pedem que você aponte o link de volta para a vaga original, o que o painel faz.
- Vagas do **Brasil** nessas fontes são poucas: elas são sobretudo remotas internacionais. Para mais vagas BR, adicione outra fonte que tenha API/feed (função parecida com `remotive()` na lista `FONTES`).
- Se uma fonte mudar o formato, o log da aba Actions mostra "FALHOU nome" e as outras continuam.
- Custo da IA: só as vagas **novas** do dia são analisadas, então costuma ser centavos por mês.
