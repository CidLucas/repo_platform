/**
 * Service para gerenciamento da Base de Conhecimento (RAG).
 * Comunica com Supabase Storage + vector_db schema para upload, listagem e remoção de documentos.
 */

import { supabase } from "../lib/supabase";

// ── Types ──────────────────────────────────────────────────────

export interface KBDocument {
    id: string;
    client_id: string;
    title: string | null;
    file_name: string;
    file_type: string | null;
    storage_path: string | null;
    source: "upload" | "chat" | "url" | "api";
    processing_mode: "simple" | "complex";
    status: "pending" | "processing" | "completed" | "failed";
    error_message: string | null;
    chunk_count: number;
    created_at: string;
    updated_at: string;
}

export interface EmbeddingProgress {
    total_chunks: number;
    embedded_chunks: number;
    progress_pct: number;
}

export type KBDocumentSource = "upload" | "chat" | "url" | "api";

// ── Constants ──────────────────────────────────────────────────

const STORAGE_BUCKET = "knowledge-base";

/** Extensions that always need Python/docling processing */
const ALWAYS_COMPLEX_EXTENSIONS = new Set([".pptx", ".xlsx"]);

// ── Helpers ────────────────────────────────────────────────────

function getExtension(fileName: string): string {
    const idx = fileName.lastIndexOf(".");
    return idx === -1 ? "" : fileName.slice(idx).toLowerCase();
}

/**
 * Decide se o arquivo precisa do processamento avançado (Python/docling).
 *
 * `.pptx`, `.xlsx` → sempre complexo.
 * `.pdf`, `.docx` → simples por padrão, a não ser que `forceComplex` esteja marcado.
 * O resto (txt, csv, etc.) → simples.
 */
export function isComplexFile(fileName: string, forceComplex = false): boolean {
    const ext = getExtension(fileName);
    if (ALWAYS_COMPLEX_EXTENSIONS.has(ext)) return true;
    if (forceComplex && (ext === ".pdf" || ext === ".docx")) return true;
    return false;
}

/** All extensions accepted for upload */
export function getAcceptedExtensions(): string {
    return ".pdf,.docx,.csv,.txt,.md,.json,.xml,.html,.xlsx,.pptx,.yaml,.yml";
}

// ── Service functions ──────────────────────────────────────────

/**
 * Lista todos os documentos do cliente.
 */
export async function listDocuments(clientId: string): Promise<KBDocument[]> {
    const { data, error } = await supabase
        .schema("vector_db")
        .from("documents")
        .select("*")
        .eq("client_id", clientId)
        .order("created_at", { ascending: false });

    if (error) throw new Error(`Erro ao listar documentos: ${error.message}`);
    return (data ?? []) as KBDocument[];
}

/**
 * Remove um documento (storage file + DB row). Chunks são removidos via ON DELETE CASCADE.
 */
export async function deleteDocument(
    documentId: string,
    storagePath: string | null
): Promise<void> {
    // 1. Remove file from storage
    if (storagePath) {
        const { error: storageError } = await supabase.storage
            .from(STORAGE_BUCKET)
            .remove([storagePath]);
        if (storageError) {
            console.warn("Erro ao remover arquivo do storage:", storageError.message);
        }
    }

    // 2. Delete document row (chunks cascade)
    const { error } = await supabase
        .schema("vector_db")
        .from("documents")
        .delete()
        .eq("id", documentId);

    if (error) throw new Error(`Erro ao deletar documento: ${error.message}`);
}

/**
 * Retorna progresso de embedding de um documento.
 */
export async function getDocumentProgress(
    documentId: string
): Promise<EmbeddingProgress> {
    const { data, error } = await supabase.rpc(
        "get_document_embedding_progress",
        { p_document_id: documentId }
    );

    if (error)
        throw new Error(`Erro ao buscar progresso: ${error.message}`);

    const row = Array.isArray(data) ? data[0] : data;
    return {
        total_chunks: row?.total_chunks ?? 0,
        embedded_chunks: row?.embedded_chunks ?? 0,
        progress_pct: row?.progress_pct ?? 0,
    };
}

/**
 * Upload de arquivo simples (≤6 MB, text-based).
 * Caminho: Storage upload → insert document row → invoke process-document Edge Function.
 */
export async function uploadSimpleFile(
    file: File,
    clientId: string,
    source: KBDocumentSource = "upload"
): Promise<string> {
    const ext = getExtension(file.name);
    const storagePath = `${clientId}/${crypto.randomUUID()}-${file.name}`;

    // 1. Upload to storage
    const { error: uploadError } = await supabase.storage
        .from(STORAGE_BUCKET)
        .upload(storagePath, file);

    if (uploadError)
        throw new Error(`Erro no upload: ${uploadError.message}`);

    // 2. Create document record
    const { data: doc, error: insertError } = await supabase
        .schema("vector_db")
        .from("documents")
        .insert({
            client_id: clientId,
            file_name: file.name,
            file_type: ext.replace(".", ""),
            storage_path: storagePath,
            source,
            processing_mode: "simple" as const,
            status: "processing" as const,
        })
        .select("id")
        .single();

    if (insertError || !doc)
        throw new Error(`Erro ao criar documento: ${insertError?.message}`);

    const documentId = doc.id;

    // 3. Invoke process-document Edge Function
    const { error: fnError } = await supabase.functions.invoke(
        "process-document",
        {
            body: {
                document_id: documentId,
                storage_path: storagePath,
                client_id: clientId,
                file_name: file.name,
                file_type: ext.replace(".", ""),
            },
        }
    );

    if (fnError)
        console.warn("Aviso: Edge Function retornou erro:", fnError.message);

    return documentId;
}

/**
 * Upload de arquivo complexo (scanned PDF, PPTX, XLSX).
 * Caminho: Storage upload → insert document row → POST file_upload_api /v1/upload/process.
 */
export async function uploadComplexFile(
    file: File,
    clientId: string,
    source: KBDocumentSource = "upload"
): Promise<string> {
    const ext = getExtension(file.name);
    const storagePath = `${clientId}/${crypto.randomUUID()}-${file.name}`;

    // 1. Upload to storage (standard — TUS can be added later for large files)
    const { error: uploadError } = await supabase.storage
        .from(STORAGE_BUCKET)
        .upload(storagePath, file);

    if (uploadError)
        throw new Error(`Erro no upload: ${uploadError.message}`);

    // 2. Create document record
    const { data: doc, error: insertError } = await supabase
        .schema("vector_db")
        .from("documents")
        .insert({
            client_id: clientId,
            file_name: file.name,
            file_type: ext.replace(".", ""),
            storage_path: storagePath,
            source,
            processing_mode: "complex" as const,
            status: "pending" as const,
        })
        .select("id")
        .single();

    if (insertError || !doc)
        throw new Error(`Erro ao criar documento: ${insertError?.message}`);

    const documentId = doc.id;

    // 3. Call file_upload_api /v1/upload/process
    const fileUploadApiUrl = import.meta.env.VITE_FILE_UPLOAD_API_URL;
    if (!fileUploadApiUrl) {
        console.warn("VITE_FILE_UPLOAD_API_URL not set, skipping complex processing");
        return documentId;
    }

    const session = await supabase.auth.getSession();
    const accessToken = session.data.session?.access_token;

    try {
        const res = await fetch(`${fileUploadApiUrl}/v1/upload/process`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
            },
            body: JSON.stringify({
                document_id: documentId,
                storage_path: storagePath,
                file_name: file.name,
                client_id: clientId,
            }),
        });

        if (!res.ok) {
            console.warn("file_upload_api retornou erro:", res.status);
        }
    } catch (err) {
        console.warn("Erro ao chamar file_upload_api:", err);
    }

    return documentId;
}

/**
 * Upload genérico — roteia automaticamente para simple ou complex.
 */
export async function uploadFile(
    file: File,
    clientId: string,
    forceComplex = false,
    source: KBDocumentSource = "upload"
): Promise<string> {
    if (isComplexFile(file.name, forceComplex)) {
        return uploadComplexFile(file, clientId, source);
    }
    return uploadSimpleFile(file, clientId, source);
}
