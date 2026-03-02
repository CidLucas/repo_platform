import type { VercelRequest, VercelResponse } from "@vercel/node";

const HUBSPOT_ACCESS_TOKEN = process.env.HUBSPOT_ACCESS_TOKEN;

export default async function handler(req: VercelRequest, res: VercelResponse) {
  // CORS headers
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  // Verificar se o token está configurado
  if (!HUBSPOT_ACCESS_TOKEN) {
    console.error("HUBSPOT_ACCESS_TOKEN não está configurado");
    return res.status(500).json({ error: "Configuração do servidor incompleta" });
  }

  const { nome, email, empresa, telefone } = req.body;

  if (!email) {
    return res.status(400).json({ error: "Email é obrigatório" });
  }

  // Separar primeiro nome e sobrenome
  const nameParts = (nome || "").trim().split(" ");
  const firstName = nameParts[0] || "";
  const lastName = nameParts.slice(1).join(" ") || "";

  // Propriedades básicas do HubSpot (apenas campos padrão)
  const properties: Record<string, string> = {
    email: email,
  };

  // Adicionar campos opcionais apenas se tiverem valor
  if (firstName) properties.firstname = firstName;
  if (lastName) properties.lastname = lastName;
  if (empresa) properties.company = empresa;
  if (telefone) properties.phone = telefone;

  try {
    console.log("Creating contact:", email);
    
    const response = await fetch("https://api.hubapi.com/crm/v3/objects/contacts", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${HUBSPOT_ACCESS_TOKEN}`,
      },
      body: JSON.stringify({ properties }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      
      // Se o contato já existe, tenta atualizar
      if (response.status === 409 && errorData.message?.includes("already exists")) {
        // Buscar o contato existente pelo email
        const searchResponse = await fetch(
          `https://api.hubapi.com/crm/v3/objects/contacts/search`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${HUBSPOT_ACCESS_TOKEN}`,
            },
            body: JSON.stringify({
              filterGroups: [
                {
                  filters: [
                    {
                      propertyName: "email",
                      operator: "EQ",
                      value: email,
                    },
                  ],
                },
              ],
            }),
          }
        );

        if (searchResponse.ok) {
          const searchData = await searchResponse.json();
          if (searchData.results?.length > 0) {
            const contactId = searchData.results[0].id;
            
            // Atualizar o contato existente
            const updateResponse = await fetch(
              `https://api.hubapi.com/crm/v3/objects/contacts/${contactId}`,
              {
                method: "PATCH",
                headers: {
                  "Content-Type": "application/json",
                  Authorization: `Bearer ${HUBSPOT_ACCESS_TOKEN}`,
                },
                body: JSON.stringify({
                  properties: {
                    firstname: firstName || undefined,
                    lastname: lastName || undefined,
                    company: empresa || undefined,
                    phone: telefone || undefined,
                  },
                }),
              }
            );

            if (updateResponse.ok) {
              return res.status(200).json({ 
                success: true, 
                message: "Contato atualizado com sucesso",
                updated: true 
              });
            }
          }
        }
        
        // Mesmo se não conseguiu atualizar, retorna sucesso (contato já existe)
        return res.status(200).json({ 
          success: true, 
          message: "Contato já cadastrado",
          existing: true 
        });
      }

      console.error("HubSpot API error:", errorData);
      return res.status(response.status).json({ 
        error: "Erro ao criar contato no HubSpot",
        details: errorData 
      });
    }

    const data = await response.json();
    return res.status(201).json({ 
      success: true, 
      contactId: data.id,
      message: "Contato criado com sucesso" 
    });

  } catch (error) {
    console.error("Error creating HubSpot contact:", error);
    return res.status(500).json({ 
      error: "Erro interno ao processar requisição" 
    });
  }
}
