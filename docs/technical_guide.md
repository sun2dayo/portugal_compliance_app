# Guia Técnico - Aplicação de Conformidade Fiscal Portuguesa para ERPNext

## 1. Visão Geral da Arquitetura

A aplicação `portugal_compliance` é uma aplicação Frappe customizada desenhada para estender o ERPNext e garantir a conformidade com os requisitos fiscais portugueses, nomeadamente a certificação de software de faturação (Portaria n.º 302/2016) e a geração do ficheiro SAF-T (PT).

**Estrutura:**
*   **`portugal_compliance` (App Root):** Contém ficheiros de configuração (`hooks.py`, `setup.py`, `requirements.txt`), documentação (`docs/`) e o módulo principal.
*   **`portugal_compliance/portugal_compliance` (Módulo Principal):**
    *   **`doctype/`:** Define os DocTypes customizados:
        *   `compliance_audit_log/`: Registo de auditoria para eventos fiscais.
        *   `document_series_pt/`: Gestão das séries de documentos e códigos ATCUD.
        *   `portugal_compliance_settings/`: Configurações globais da aplicação (chaves, certificados).
        *   `taxonomy_code/`: Armazena os códigos de taxonomia oficiais para o SAF-T.
    *   **`page/`:**
        *   `saft_pt_generator/`: Interface de utilizador para gerar o ficheiro SAF-T.
    *   **`fixtures/`:** Contém dados exportados, como `custom_field.json` (campos adicionados a DocTypes standard) e `print_format.json`.
    *   **`hooks/`:** Scripts Python que implementam lógica central:
        *   `doc_events.py`: Lógica acionada por eventos de documentos (save, submit, cancel), incluindo geração de ATCUD/QR e validação de inviolabilidade.
        *   `signing.py`: Lógica para assinatura digital e encadeamento de hash.
        *   `print_utils.py`: Funções utilitárias para formatos de impressão (ex: gerar QR code base64).
    *   **`saft/`:** Módulo dedicado à geração do SAF-T (PT):
        *   `generator.py`: Classe principal `SaftGenerator` que constrói o XML.
        *   `utils.py`: Funções utilitárias para formatação de datas, números, obtenção de ATCUD, etc.
    *   **`config/`:** Configurações do módulo, como `desktop.py` para ícones na área de trabalho.
    *   **`print_format/`:** Formatos de impressão customizados (ex: `sales_invoice_pt/`).

## 2. Componentes Principais

### 2.1. Geração SAF-T (PT) (`saft/generator.py`)

*   **Classe `SaftGenerator`:** Orquestra a criação do ficheiro XML.
*   **Namespaces:** Define os namespaces XML corretos para a versão 1.04_01.
*   **Estrutura:** Constrói as secções principais: `Header`, `MasterFiles`, `SourceDocuments` (com `SalesInvoices`). As secções `GeneralLedgerEntries`, `MovementOfGoods`, `WorkingDocuments`, `Payments` não estão implementadas nesta versão mas podem ser adicionadas.
*   **`_build_header()`:** Preenche os dados da empresa, ano fiscal, software, etc., com base na `Company` e `Portugal Compliance Settings`.
*   **`_build_master_files()`:** Chama funções para gerar:
    *   `_build_general_ledger_accounts()`: Exporta contas do `Chart of Accounts`, incluindo o `custom_taxonomy_code`.
    *   `_build_customers()`: Exporta clientes ativos, incluindo morada de faturação.
    *   `_build_suppliers()`: Exporta fornecedores ativos, incluindo morada de faturação.
    *   `_build_products()`: Exporta itens, usando `custom_saft_product_type`.
    *   `_build_tax_table()`: Exporta taxas de IVA (`Sales Taxes and Charges Template`) usando `custom_saft_tax_code` e `custom_saft_exemption_reason_code`.
*   **`_build_source_documents()`:** Chama funções para gerar secções de documentos:
    *   `_build_sales_invoices()`: Exporta faturas e notas de crédito (`Sales Invoice`, `Sales Invoice Return`) do período, incluindo status, hash (assinatura), totais e linhas com detalhes de IVA baseados nos campos customizados.
*   **Utils (`saft/utils.py`):** Contém funções para formatar datas, datetimes, moeda, obter datas do ano fiscal, extrair número sequencial, e obter o ATCUD.

### 2.2. Geração ATCUD e QR Code (`hooks/doc_events.py`, `saft/utils.py`)

*   **DocType `Document Series PT`:** Armazena a relação entre a série de numeração ERPNext, o tipo de documento AT, e o código de validação ATCUD (obtido da AT - comunicação não implementada).
*   **`get_atcud()` (`saft/utils.py`):** Função central que busca o código de validação em `Document Series PT` com base na série do documento.
*   **`_ensure_atcud_and_qr_content()` (`hooks/doc_events.py`):** Chamada no `before_save` e `on_submit`. Garante que o ATCUD é obtido e que a string do QR Code é construída.
*   **`_build_qr_code_string()` (`hooks/doc_events.py`):** Constrói a string formatada para o QR Code conforme especificações da AT, buscando dados da empresa, cliente, documento, totais de IVA (calculados a partir dos impostos do documento e dos `custom_saft_tax_code`), ATCUD, e número do certificado. O campo `Q` (hash da assinatura) é preenchido inicialmente com 'AAAA' e atualizado no `on_submit` pela função `sign_document`.
*   **Campos Customizados:** `custom_atcud` e `custom_qr_code_content` são adicionados aos DocTypes relevantes para armazenar estes valores.
*   **Formato de Impressão:** A função `get_qr_code_base64()` (`hooks/print_utils.py`) é usada no template Jinja (`sales_invoice_pt.html`) para gerar a imagem QR Code a partir do `custom_qr_code_content`.

### 2.3. Assinatura Digital e Encadeamento de Hash (`hooks/signing.py`)

*   **`sign_document()`:** Chamada no `on_submit` após a geração final do QR Code.
*   **`get_previous_document_hash()`:** Busca o `custom_document_hash` do documento anterior *submetido* na mesma série e DocType. Retorna "0" se for o primeiro documento.
*   **Construção da String:** Cria a string para assinatura no formato `DataDeEmissao;DataHoraDeEmissao;IdentificadorUnicoDoc;ValorTotal;HashAnterior` (Despacho 8632/2014).
*   **Cálculo do Hash Atual:** Calcula o hash SHA-256 da string *sem* o hash anterior e armazena em `custom_document_hash` (para o próximo documento usar).
*   **Carregamento da Chave:** Lê a chave privada PEM do caminho especificado em `Portugal Compliance Settings`, usando a senha se fornecida.
*   **Assinatura:** Assina a string *com* o hash anterior usando RSA com SHA-256 e padding PKCS1v15 (verificar se AT exige SHA-1).
*   **Armazenamento:** Guarda a assinatura Base64 em `custom_digital_signature`, o hash atual em `custom_document_hash`, e o hash anterior em `custom_previous_hash`.
*   **Atualização QR Code:** Atualiza o campo `Q:` na string `custom_qr_code_content` com os 4 primeiros caracteres da assinatura Base64.
*   **`db_set`:** Usa `frappe.db.set_value` para guardar os campos sem disparar novamente os hooks de save.

### 2.4. Registo de Auditoria e Inviolabilidade (`doctype/compliance_audit_log/`, `hooks/doc_events.py`)

*   **DocType `Compliance Audit Log`:** Armazena registos imutáveis (permissões restritas) com timestamp, utilizador, tipo de evento, referência ao documento e detalhes.
*   **`create_compliance_log()`:** Função para criar entradas no log. Chamada a partir dos hooks.
*   **Hooks (`hooks/doc_events.py`):**
    *   `handle_before_save`: Regista evento "Create" para novos documentos.
    *   `handle_on_submit`: Regista evento "Submit" após assinatura.
    *   `handle_on_cancel`: Regista evento "Cancel".
    *   `handle_validate_submitted`: Chamado na validação de documentos já submetidos (docstatus=1). Compara campos críticos (incluindo itens) com a versão guardada na BD. Se houver alterações, regista um evento "Update Attempt (Submitted)" e lança uma exceção para impedir a gravação, garantindo a inviolabilidade.

## 3. DocTypes Customizados

*   **`Portugal Compliance Settings` (Single):** Armazena configurações globais (caminho/senha da chave, nº certificado, NIF produtor, ID/versão produto).
*   **`Document Series PT`:** Mapeia séries ERPNext a tipos de documento AT e armazena o código de validação ATCUD.
*   **`Taxonomy Code`:** Armazena os códigos de taxonomia oficiais para mapeamento de contas.
*   **`Compliance Audit Log`:** Registo imutável de eventos fiscais.

## 4. Campos Customizados (`fixtures/custom_field.json`)

Campos adicionados a DocTypes standard:
*   **Account:** `custom_taxonomy_code` (Link: Taxonomy Code)
*   **Item:** `custom_saft_product_type` (Select: P, S, M, O)
*   **Sales Taxes and Charges Template:** `custom_saft_tax_code` (Select: RED, INT, NOR, ISE, OUT), `custom_saft_exemption_reason_code` (Data)
*   **Sales Invoice, Delivery Note, Sales Invoice Return (Credit Note):**
    *   `custom_atcud` (Data, Read Only)
    *   `custom_qr_code_content` (Small Text, Read Only)
    *   `custom_digital_signature` (Small Text, Read Only)
    *   `custom_document_hash` (Data, Read Only)
    *   `custom_previous_hash` (Data, Read Only)

## 5. Hooks (`hooks.py`)

*   **`doc_events`:** Mapeia eventos de DocTypes (Sales Invoice, Delivery Note, etc.) para as funções em `hooks/doc_events.py` (`handle_before_save`, `handle_on_submit`, `handle_on_cancel`, `handle_validate_submitted`).
*   **`fixtures`:** Inclui `Custom Field`, `Print Format`, `Compliance Audit Log` para exportação/importação.
*   **`jinja`:** Expõe o método `get_qr_code_base64` para uso em templates de impressão.

## 6. Dependências (`requirements.txt`)

*   **`lxml`:** Para processamento XML (geração SAF-T).
*   **`cryptography`:** Para assinatura digital e hashing.
*   **`qrcode[pil]`:** Para geração de imagens QR Code.
*   **`requests`:** (Potencialmente necessário para futura comunicação com a AT).

## 7. Pontos de Extensão e Melhoria

*   **Comunicação AT:** Implementar a comunicação via webservice com a AT para validação/registo de séries e obtenção automática do código de validação ATCUD.
*   **Validação XSD:** Integrar validação XSD do ficheiro SAF-T gerado antes de o disponibilizar.
*   **Cálculo de IVA/Imposto Selo:** Refinar a lógica no `_build_qr_code_string` e `_build_sales_invoices` para cobrir todos os cenários de impostos, incluindo Imposto Selo.
*   **Mapeamento DocType:** Expandir `DOCTYPE_TO_AT_CODE` para cobrir todos os documentos fiscais relevantes usados.
*   **SAF-T Completo:** Implementar as secções `GeneralLedgerEntries`, `MovementOfGoods`, `WorkingDocuments`, `Payments` se necessário.
*   **Saldos SAF-T:** Implementar a lógica para calcular e incluir saldos de abertura/fecho em `GeneralLedgerAccounts`.
*   **Referências (Notas Crédito):** Adicionar lógica para incluir referências ao documento original em notas de crédito no SAF-T.
*   **Testes Automatizados:** Criar testes unitários e de integração para garantir a robustez das funcionalidades.
*   **Hashing/Chaining do Log:** Implementar hashing e encadeamento no próprio `Compliance Audit Log` para segurança adicional.
