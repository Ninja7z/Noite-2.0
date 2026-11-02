# Segurança de operações do workspace

**Estado:** proposta para operações de renomear e excluir. O terminal foi implementado separadamente; consulte `docs/TERMINAL.md` e `tests/test_terminal.py` para o comportamento e a validação atuais.

## Limites e modelo de ameaça

- O workspace é a única raiz autorizada. Caminhos absolutos fora dela, traversal, links simbólicos e junctions são rejeitados após validar cada componente no momento da operação.
- A árvore oculta segredos, caches e dependências. Operações não podem usar esses caminhos, mesmo que sejam digitados manualmente.
- A aprovação humana vale para uma operação concreta e exibe caminho de origem, destino e efeito. O modelo não aprova nem dispara operações.
- Nenhuma operação sobrescreve arquivo ou pasta existente. Uma colisão aborta sem alterar conteúdo.
- Leitura, busca, gravação, renomeação e exclusão revalidam raiz e alvo imediatamente antes do acesso para reduzir troca de symlink entre seleção e uso.
- Arquivos abertos com mudanças não salvas bloqueiam rename/delete até o usuário salvar ou descartar conscientemente; abas limpas são atualizadas após rename e removidas após delete.
- Exclusão de arquivo exige confirmação e é limitada a arquivos regulares. Exclusão de pasta é limitada a diretórios vazios; não há recursão implícita.
- Falhas deixam a árvore e os buffers intactos. A árvore só é atualizada depois de operação concluída.

## Terminal (implementado separadamente)

- Executar apenas comandos configurados pelo usuário em allowlist; texto do modelo nunca vira comando executável.
- Um comando submetido pelo usuário mostra executável e argumentos completos e pede confirmação antes de iniciar.
- shell=False; diretório de trabalho validado dentro do workspace; ambiente filho mínimo e segredos não são copiados automaticamente.
- Timeout, limite de saída, cancelamento e encerramento da árvore de processos; stdout/stderr são dados não confiáveis e não autorizam novas ações. Os limites concretos estão documentados em `docs/TERMINAL.md`.
- Sem elevação de privilégios. Sem terminal remoto ou acesso a paths fora do workspace.

## Critérios de validação

- Testes de traversal, symlink/junction, colisão de destino, arquivo secreto, buffer dirty e diretório não vazio.
- Testes UI de cancelar/aprovar, atualização da árvore e preservação das abas.
- Para rename/delete: comandos de aprovação, colisão, traversal, buffers abertos e preservação da árvore.
- O terminal existente é coberto por `tests/test_terminal.py`; rename/delete continuam pendentes e exigem revisão própria antes de implementação.
