import { Box, Text, Code, Link, UnorderedList, OrderedList, ListItem, Heading, Divider, Table, Thead, Tbody, Tr, Th, Td } from '@chakra-ui/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import type { Components } from 'react-markdown';

interface MarkdownMessageProps {
    content: string;
    isUser?: boolean;
}

/**
 * Renders markdown content with Chakra UI components.
 * Supports GFM (GitHub Flavored Markdown) for tables, strikethrough, etc.
 *
 * Styled for clean, readable AI responses.
 */
export const MarkdownMessage = ({ content, isUser = false }: MarkdownMessageProps) => {
    const textColor = isUser ? 'white' : 'gray.800';
    const linkColor = isUser ? 'blue.200' : 'blue.600';
    const codeBackground = isUser ? 'whiteAlpha.200' : 'gray.100';
    const tableBorderColor = isUser ? 'whiteAlpha.300' : 'gray.200';
    const strongColor = isUser ? 'white' : 'gray.900';
    const mutedColor = isUser ? 'whiteAlpha.800' : 'gray.600';

    const components: Components = {
        // Paragraphs - clean spacing
        p: ({ children }) => (
            <Text
                mb={3}
                fontSize="15px"
                fontFamily="'Inter', 'Noto Sans', -apple-system, sans-serif"
                lineHeight="1.65"
                color={textColor}
                letterSpacing="-0.01em"
                _last={{ mb: 0 }}
            >
                {children}
            </Text>
        ),

        // Headings - clear hierarchy
        h1: ({ children }) => (
            <Heading as="h1" size="lg" mb={3} mt={4} color={textColor} fontWeight="600" _first={{ mt: 0 }}>
                {children}
            </Heading>
        ),
        h2: ({ children }) => (
            <Heading as="h2" size="md" mb={2} mt={4} color={textColor} fontWeight="600" _first={{ mt: 0 }}>
                {children}
            </Heading>
        ),
        h3: ({ children }) => (
            <Heading as="h3" size="sm" mb={2} mt={3} color={textColor} fontWeight="600" _first={{ mt: 0 }}>
                {children}
            </Heading>
        ),

        // Bold - slightly darker for emphasis
        strong: ({ children }) => (
            <Text as="strong" fontWeight="600" color={strongColor}>
                {children}
            </Text>
        ),
        em: ({ children }) => (
            <Text as="em" fontStyle="italic" color={mutedColor}>
                {children}
            </Text>
        ),

        // Links
        a: ({ href, children }) => (
            <Link href={href} color={linkColor} isExternal textDecoration="underline" _hover={{ textDecoration: 'none' }}>
                {children}
            </Link>
        ),

        // Lists - tighter spacing
        ul: ({ children }) => (
            <UnorderedList ml={4} mb={3} spacing={1} color={textColor} styleType="disc">
                {children}
            </UnorderedList>
        ),
        ol: ({ children }) => (
            <OrderedList ml={4} mb={3} spacing={1} color={textColor}>
                {children}
            </OrderedList>
        ),
        li: ({ children }) => (
            <ListItem
                fontSize="15px"
                fontFamily="'Inter', 'Noto Sans', -apple-system, sans-serif"
                lineHeight="1.5"
                pl={1}
            >
                {children}
            </ListItem>
        ),

        // Code - monospace with subtle background
        code: ({ className, children }) => {
            const isBlock = className?.includes('language-');
            if (isBlock) {
                return (
                    <Box
                        as="pre"
                        bg={codeBackground}
                        p={3}
                        borderRadius="lg"
                        overflowX="auto"
                        my={3}
                        fontSize="13px"
                        fontFamily="'JetBrains Mono', 'Fira Code', 'SF Mono', monospace"
                        border="1px solid"
                        borderColor={tableBorderColor}
                    >
                        <Code bg="transparent" color={textColor} whiteSpace="pre-wrap">
                            {children}
                        </Code>
                    </Box>
                );
            }
            return (
                <Code
                    bg={codeBackground}
                    color={textColor}
                    px={1.5}
                    py={0.5}
                    borderRadius="md"
                    fontSize="14px"
                    fontWeight="500"
                >
                    {children}
                </Code>
            );
        },

        // Horizontal rule
        hr: () => <Divider my={4} borderColor={tableBorderColor} />,

        // Tables (GFM) - clean borders
        table: ({ children }) => (
            <Box overflowX="auto" my={3}>
                <Table size="sm" variant="simple" borderWidth="1px" borderColor={tableBorderColor} borderRadius="lg">
                    {children}
                </Table>
            </Box>
        ),
        thead: ({ children }) => (
            <Thead bg={isUser ? 'whiteAlpha.100' : 'gray.50'}>
                {children}
            </Thead>
        ),
        tbody: ({ children }) => <Tbody>{children}</Tbody>,
        tr: ({ children }) => (
            <Tr borderBottomWidth="1px" borderColor={tableBorderColor}>
                {children}
            </Tr>
        ),
        th: ({ children }) => (
            <Th
                color={textColor}
                fontSize="12px"
                fontWeight="600"
                borderColor={tableBorderColor}
                py={2}
            >
                {children}
            </Th>
        ),
        td: ({ children }) => (
            <Td
                color={textColor}
                fontSize="13px"
                borderColor={tableBorderColor}
                py={2}
            >
                {children}
            </Td>
        ),

        // Blockquote
        blockquote: ({ children }) => (
            <Box
                borderLeftWidth="3px"
                borderLeftColor={isUser ? 'whiteAlpha.500' : 'gray.300'}
                pl={3}
                my={2}
                fontStyle="italic"
                color={isUser ? 'whiteAlpha.800' : 'gray.600'}
            >
                {children}
            </Box>
        ),
    };

    return (
        <Box>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeSanitize]}
                components={components}
            >
                {content}
            </ReactMarkdown>
        </Box>
    );
};

export default MarkdownMessage;
