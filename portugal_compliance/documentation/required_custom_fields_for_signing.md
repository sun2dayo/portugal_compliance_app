# Campos Personalizados Necessários para Documentos Fiscais (Ex: Sales Invoice)

Para suportar a assinatura digital, o encadeamento de hashes e a geração de QR Code, os seguintes campos personalizados precisam ser adicionados aos DocTypes fiscais relevantes (como Fatura de Venda/Sales Invoice, Nota de Crédito, etc.) na aplicação `portugal_compliance`.

Estes campos serão preenchidos automaticamente pela função `sign_document_and_generate_qr` (localizada em `portugal_compliance.utils.fiscal_signature`) quando um documento fiscal for submetido, conforme configurado no `hooks.py`.

## Campos Requeridos:

1.  **`pt_serie_fiscal`**
    *   **Label:** Série Fiscal
    *   **Tipo de Campo:** Link
    *   **Opções:** Serie de Documento Fiscal
    *   **Descrição:** Referência à série de documento fiscal utilizada para este documento. Essencial para obter o ATCUD e gerir a sequência.
    *   **Obrigatório:** Sim

2.  **`pt_atcud`**
    *   **Label:** ATCUD
    *   **Tipo de Campo:** Data
    *   **Descrição:** Código Único do Documento, gerado a partir da série fiscal e do número sequencial. Será preenchido após a obtenção do número sequencial da série.
    *   **Apenas Leitura:** Sim (após preenchimento inicial)

3.  **`pt_document_type_code`**
    *   **Label:** Código do Tipo de Documento (para QR)
    *   **Tipo de Campo:** Data
    *   **Descrição:** Código abreviado do tipo de documento (ex: FT, NC, FS) usado na string do QR Code. Pode ser derivado da Série Fiscal.
    *   **Apenas Leitura:** Sim (geralmente preenchido programaticamente)

4.  **`pt_hash_dados_documento_sha1`**
    *   **Label:** Hash SHA-1 dos Dados do Documento (para encadeamento)
    *   **Tipo de Campo:** Small Text (ou Text)
    *   **Descrição:** Hash SHA-1 da string de dados da fatura atual (Data;Hora;Numero;Total;HashAnterior). Usado como `previous_invoice_hash` para o próximo documento na mesma série.
    *   **Apenas Leitura:** Sim

5.  **`pt_assinatura_digital_rsa`**
    *   **Label:** Assinatura Digital RSA (Base64)
    *   **Tipo de Campo:** Text (ou Long Text)
    *   **Descrição:** Assinatura digital RSA dos dados do documento, codificada em Base64.
    *   **Apenas Leitura:** Sim

6.  **`pt_assinatura_4_caracteres`**
    *   **Label:** Caracteres da Assinatura (para Impressão)
    *   **Tipo de Campo:** Data
    *   **Descrição:** Os 4 caracteres específicos (1ª, 11ª, 21ª, 31ª) do hash SHA1 da string de dados do documento, para serem impressos no documento fiscal.
    *   **Apenas Leitura:** Sim

7.  **`pt_qr_code_string`**
    *   **Label:** String do QR Code
    *   **Tipo de Campo:** Text (ou Long Text)
    *   **Descrição:** A string completa de dados utilizada para gerar o QR Code.
    *   **Apenas Leitura:** Sim

8.  **`pt_qr_code_imagem`**
    *   **Label:** Imagem do QR Code
    *   **Tipo de Campo:** Attach Image
    *   **Descrição:** A imagem do QR Code gerada para este documento.
    *   **Apenas Leitura:** Sim

## Notas Adicionais:

*   Os campos existentes no DocType fiscal (ex: `company`, `naming_series` (se usado para a série fiscal antes da introdução do `pt_serie_fiscal`), `posting_date`, `posting_time`, `grand_total`, `net_total`, `tax_id` do cliente) serão utilizados como input para a função de assinatura e geração do QR Code.
*   A lógica para obter o `previous_invoice_hash` (campo `pt_hash_dados_documento_sha1` do documento anterior na mesma série) precisa ser robusta e considerar a ordenação correta dos documentos.
*   A impressão destes campos nos formatos de impressão relevantes (especialmente `pt_assinatura_4_caracteres` e `pt_qr_code_imagem`) será uma etapa subsequente.
*   É crucial que estes campos sejam configurados como "Apenas Leitura" após o seu preenchimento programático para garantir a imutabilidade exigida pela AT.

