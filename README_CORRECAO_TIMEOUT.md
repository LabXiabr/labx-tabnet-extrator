# LABX — correção de timeout no FTP

## Diagnóstico
Dois lotes falharam ao conectar ao FTP do DATASUS; o encerramento com `ftp.quit()` gerava um erro secundário. O upload de artefatos sem arquivos também falhava.

## Mudanças
- Até 3 tentativas de conexão/listagem e download, com reconexão e espera curta.
- `ftp.close()` no encerramento, sem mascarar o erro com `QUIT`.
- `resumo_lote.json` gerado inclusive em falha de conexão.
- Upload de artefatos ausentes vira aviso; o job de download continua falhando se não baixar todos os arquivos esperados.
- Mantidos `.dbc` originais, SHA-256, manifestos e divisão por UFs.

## Atenção
Não faz retry automático de todo o workflow nem recupera artefatos de outra execução; os jobs bem-sucedidos da execução anterior permanecem disponíveis em Actions.

## Testar
`python -m unittest discover -s tests -p 'test_baixar_dbc_actions.py' -v`
`python scripts/gerar_opcoes_workflow.py --check`

## Aplicação
Copie os arquivos do ZIP para a raiz do projeto e revise o diff antes do commit.
