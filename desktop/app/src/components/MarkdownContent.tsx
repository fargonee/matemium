import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";

interface MarkdownContentProps {
  content: string;
}

const sanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    code: [
      ...(defaultSchema.attributes?.code || []),
      ["className", "language-math", "math-inline", "math-display"],
    ],
    span: [
      ...(defaultSchema.attributes?.span || []),
      ["className", "math-inline", "math-display"],
    ],
  },
};

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[
          [rehypeSanitize, sanitizeSchema],
          [rehypeKatex, { strict: "warn", throwOnError: false, trust: false }],
        ]}
        components={{
          a: ({ href, children }) => {
            if (!isSafeHref(href)) return <>{children}</>;
            return (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          },
          code: ({ className, children, ...props }) => (
            <code className={className} {...props}>
              {children}
            </code>
          ),
          table: ({ children }) => (
            <div className="markdown-table-wrap">
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function isSafeHref(href: string | undefined): href is string {
  if (!href) return false;
  return /^(https?:|mailto:)/i.test(href) || href.startsWith("#");
}
