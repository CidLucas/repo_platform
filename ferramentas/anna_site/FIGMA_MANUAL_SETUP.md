# 🎨 Anna Maria Maiolino - Setup Manual no Figma

## Componentes Criados via MCP

### ✅ Já criados no Figma:
1. **HOME - Anna Maria Maiolino** (Frame 1440x1080)
   - Título principal
   - CTA "entrar no site"

2. **MENU - Anna Maria Maiolino** (Frame 1440x1080)
   - Logo
   - Items de menu
   - Copyright

3. **LINHA DO TEMPO** (Frame 1440x5000)
   - Título da página
   - Seções: Exposições Individuais, Coletivas, Palestras, etc.

4. **Component: Header** (1440x120)
   - Logo "ANNA MARIA MAIOLINO"
   - Nav Links (6 itens)

5. **Component: Footer** (1440x80)
   - Copyright

6. **Component: Card Obra** (320x256)
   - Image Placeholder (320x240)
   - (falta adicionar título e descrição)

---

## 📐 Especificações de Design

### Cores
```
Primary Text: #000000
Secondary Text: #333333
Caption: #444444
Background: #FFFFFF
Card BG: #F7F7F7
Placeholder: #D9D9D9
```

### Tipografia

#### Header/Logo
- Font: Inter Bold (ou Times para fidelidade ao original)
- Size: 24px
- Color: #000000

#### Navegação
- Font: Inter Regular (ou Times)
- Size: 16px
- Line-height: 19px
- Color: #000000

#### Títulos de Página
- Font: Inter Bold
- Size: 48px
- Color: #000000

#### Títulos de Seção
- Font: Inter Bold
- Size: 24px
- Color: #000000

#### Body
- Font: Inter Regular
- Size: 16px
- Line-height: 24px
- Color: #000000

#### Caption/Copyright
- Font: Inter Regular
- Size: 12px
- Line-height: 18px
- Color: #444444

---

## 📋 Conteúdo para Inserir Manualmente

### Página: EXPOSIÇÕES E OBRAS
Copie do arquivo: `anna_site_content_complete.json` → seção "obras"

Exemplos de cards:
1. **Por um Fio [By a Thread]**, SCAD, Savannah, 2020
2. **Terra Modelada** [Modeled Earth] series, 1994/2020
3. Vista da exposição, SCAD Museum of Art

### Página: TEXTOS CRÍTICOS
Autores principais:
- Paulo Miyada - "O sopro interminável"
- Michael Asbury
- Diego Sileo
- Helena Tatay
- Catherine de Zegher
- Marcio Doctors

### Página: SINE DIE
- Filmografia
- "É" [It Is]
- "In Atto" (No Lugar) [In Place]
- "É O Que É" [It Is What It Is]

### Página: CONTATO
Formulário:
- Nome [Name]
- Email [Email]
- Sua mensagem [Your message]
- Botão: ENVIAR [SEND]

---

## 📁 Arquivos de Referência

1. **Textos completos:** `ferramentas/anna_site_content_complete.json`
2. **Imagens baixadas:** `ferramentas/anna_images/` (71 arquivos)
3. **CSS extraído:** `ferramentas/anna_site/css/`
4. **Especificações:** `ferramentas/anna_site/FIGMA_SPECS.md`
5. **Layout do menu:** `ferramentas/anna_site/figma_elements_menu.json`

---

## 🔧 Para Continuar via MCP

Quando o MCP voltar a funcionar, execute:

```
bb7_create_text({
  text: "Título da Obra",
  parentId: "2:66",
  x: 16,
  y: 256,
  fontSize: 16,
  fontWeight: 700
})
```

