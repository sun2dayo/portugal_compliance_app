# Guia do Utilizador - Conformidade Fiscal Portuguesa para ERPNext

## Introdução

Esta aplicação (`portugal_compliance`) estende o ERPNext para cumprir os requisitos de certificação de software de faturação em Portugal, conforme definido pela Autoridade Tributária e Aduaneira (AT), incluindo a Portaria n.º 302/2016 e legislação relacionada.

Funcionalidades principais:
*   Geração do ficheiro SAF-T (PT) no formato standard.
*   Geração automática do Código Único de Documento (ATCUD).
*   Geração automática de QR Code em documentos relevantes.
*   Assinatura digital qualificada de documentos fiscais.
*   Encadeamento de hash para garantir a sequencialidade e integridade.
*   Registo de auditoria detalhado (Compliance Audit Log).
*   Mecanismos para garantir a inviolabilidade dos documentos submetidos.

Este guia descreve como instalar, configurar e utilizar esta aplicação.

## Instalação

1.  **Obter a Aplicação:** Descarregue ou clone o código da aplicação `portugal_compliance` para a pasta `apps` da sua instalação Frappe Bench.
2.  **Instalar a Aplicação:** Navegue até à pasta do seu bench e execute os seguintes comandos:
    ```bash
    # Instalar dependências Python
    bench pip install -e apps/portugal_compliance

    # Instalar a aplicação no seu site
    bench --site [your-site-name] install-app portugal_compliance

    # Executar migrações (isto irá criar DocTypes e Campos Customizados)
    bench --site [your-site-name] migrate
    ```
3.  **Reiniciar o Bench:** `bench restart`

## Configuração Inicial

Após a instalação, são necessárias algumas configurações para que a aplicação funcione corretamente.

### 1. Configurações de Conformidade de Portugal

Aceda a `Pesquisar > Portugal Compliance Settings`.

*   **Caminho da Chave Privada:** Insira o caminho absoluto no servidor onde o ficheiro da chave privada (.pem ou .key) para a assinatura digital está armazenado (ex: `/path/to/your/private_key.pem`). Certifique-se de que o utilizador do Frappe tem permissões de leitura para este ficheiro.
*   **Senha da Chave Privada:** Se a sua chave privada estiver protegida por senha, insira-a aqui.
*   **Número do Certificado do Software:** Insira o número de certificado atribuído pela AT ao seu software (ex: `1234/AT`).
*   **NIF do Produtor do Software:** Insira o NIF da entidade que produz/fornece este software de conformidade.
*   **ID do Produto:** Um identificador para esta aplicação (ex: `ERPNext-PTCompliance/1.0`).
*   **Versão do Produto:** A versão desta aplicação de conformidade (ex: `1.0`).

Guarde as configurações.

### 2. Séries de Documentos (Document Series PT)

Aceda a `Pesquisar > Document Series PT > Novo`.

Este DocType é crucial para a geração do ATCUD. Para cada série de numeração que será usada em documentos fiscais (Faturas, Guias, etc.), é necessário criar um registo aqui.

*   **Série de Numeração:** Selecione a série de numeração existente no ERPNext (ex: `INV-`, `DN-`).
*   **Tipo de Documento (AT):** Selecione o código oficial da AT para o tipo de documento associado a esta série (ex: `FT` para Fatura, `GT` para Guia de Transporte, `NC` para Nota de Crédito).
*   **Data de Início:** A data a partir da qual esta série será usada para comunicação com a AT.
*   **Código de Validação da Série (ATCUD):** *Este campo será preenchido automaticamente após a comunicação (ainda não implementada) com a AT.* Por agora, pode ser deixado em branco ou preenchido manualmente com um valor de teste se necessário.
*   **Meio de Processamento:** Selecione o meio (ex: Programa Informático).

**Nota Importante:** A comunicação automática com a AT para obter o código de validação da série ainda não está implementada nesta versão. Este passo terá de ser feito manualmente ou através de desenvolvimento adicional.

### 3. Modelos de Impostos e Taxas (Sales Taxes and Charges Template)

Para cada taxa de IVA (ou isenção) que utiliza, configure os campos SAF-T:

Aceda a `Contabilidade > Configurações > Modelo de Impostos e Taxas`.

Selecione ou crie um modelo de imposto:
*   **SAF-T Tax Code:** Selecione o código de IVA correspondente para o SAF-T (PT): `RED` (Reduzida), `INT` (Intermédia), `NOR` (Normal), `ISE` (Isenta), `OUT` (Outra).
*   **SAF-T Exemption Reason Code:** *Apenas visível se 'SAF-T Tax Code' for 'ISE'*. Insira o código oficial do motivo de isenção (ex: `M01`, `M05`, `M99`). Consulte a documentação da AT para os códigos corretos.

### 4. Contas (Chart of Accounts)

Para o mapeamento correto no SAF-T, associe códigos de taxonomia às suas contas contabilísticas.

Aceda a `Contabilidade > Plano de Contas`.

Selecione uma conta:
*   **Taxonomy Code (SAF-T PT):** Selecione o código de taxonomia oficial aplicável a esta conta. Pode pesquisar ou criar novos códigos em `Pesquisar > Taxonomy Code` (este DocType deve ser preenchido com os códigos oficiais da AT).

### 5. Itens (Item)

Classifique os seus produtos e serviços para o SAF-T.

Aceda a `Stock > Itens > Item`.

Selecione ou crie um item:
*   **SAF-T Product Type:** Selecione o tipo de produto para o SAF-T: `P` (Produto), `S` (Serviço), `M` (Mercadoria), `O` (Outros).

## Utilização

### Criação e Submissão de Documentos

Ao criar documentos fiscais relevantes (Faturas, Guias de Remessa, Notas de Crédito, etc.) que utilizem uma série configurada em `Document Series PT`:

1.  **Rascunho:** Ao guardar o documento como rascunho, os campos `ATCUD` e `QR Code Content` serão preenchidos automaticamente (se a série estiver corretamente configurada).
2.  **Submissão:** Ao submeter o documento:
    *   O documento será assinado digitalmente usando a chave privada configurada.
    *   O hash do documento anterior na mesma série será recuperado.
    *   A assinatura digital (`custom_digital_signature`), o hash do documento atual (`custom_document_hash`) e o hash anterior (`custom_previous_hash`) serão guardados no documento.
    *   O conteúdo do QR Code será atualizado com os 4 primeiros caracteres da assinatura.
    *   Um registo será criado no `Compliance Audit Log`.

### Visualização de Campos de Conformidade

Nos documentos submetidos, pode encontrar os seguintes campos (alguns podem estar ocultos por defeito, use "Personalizar Formulário" para os mostrar se necessário):
*   **ATCUD:** O Código Único de Documento.
*   **QR Code Content:** A string completa usada para gerar o QR Code.
*   **Digital Signature:** A assinatura digital (codificada em Base64).
*   **Document Hash:** O hash deste documento.
*   **Previous Document Hash:** O hash do documento anterior na cadeia.

O **QR Code** será visível no formato de impressão padrão `Sales Invoice PT` (e outros formatos que o incluam).

### Geração do Ficheiro SAF-T (PT)

1.  Aceda a `Pesquisar > SAF-T PT Generator`.
2.  Selecione a **Empresa** e o **Ano Fiscal** desejados.
3.  Clique em **Gerar SAF-T (PT)**.
4.  O sistema irá gerar o ficheiro XML e disponibilizá-lo para download.
5.  Um registo será criado no `Compliance Audit Log`.

### Registo de Auditoria (Compliance Audit Log)

Aceda a `Pesquisar > Compliance Audit Log`.

Este ecrã lista todos os eventos relevantes registados pela aplicação de conformidade:
*   Criação de documentos (rascunho).
*   Submissão de documentos (com hash).
*   Cancelamento de documentos.
*   Tentativas de alteração de documentos submetidos (bloqueadas).
*   Geração do ficheiro SAF-T.
*   Comunicação de séries (a implementar).

Este registo ajuda a garantir a rastreabilidade e a conformidade.

### Inviolabilidade dos Documentos

Uma vez que um documento fiscal é submetido, a aplicação impede a alteração de campos críticos (como datas, valores, cliente, itens). Qualquer tentativa de alteração resultará num erro e será registada no `Compliance Audit Log`. Se forem necessárias correções, o documento original deve ser cancelado e um novo documento (ou nota de crédito/débito) deve ser emitido.

## Limitações e Próximos Passos

*   A comunicação automática com a AT para validação de séries não está implementada.
*   A lógica de cálculo de IVA e Imposto Selo deve ser revista para cenários complexos.
*   O mapeamento de DocTypes para códigos AT pode necessitar de ajustes.
*   A recuperação de saldos de contas para o SAF-T não está implementada.
*   Faltam secções opcionais do SAF-T (Guias, Pagamentos, etc.).

Consulte a documentação técnica para mais detalhes sobre a implementação.
