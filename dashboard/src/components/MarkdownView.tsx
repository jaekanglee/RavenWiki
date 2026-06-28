import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeHighlight from "rehype-highlight";
import { wikilinkPlugin } from "../lib/wikilink";

export function MarkdownView({ content, vault }: { content: string; vault: string }) {
  console.log("[Raven-Debug] MarkdownView mount, content length=", content?.length);
  return (
    <article className="prose dark:prose-invert max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath, wikilinkPlugin(vault)]}
        rehypePlugins={[rehypeKatex, rehypeHighlight]}
      >
        {content}
      </ReactMarkdown>
    </article>
  );
}
