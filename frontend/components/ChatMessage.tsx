import clsx from "clsx";
import { BrainCircuit, User } from "lucide-react";
import type { ChatMessage as ChatMessageType } from "@/types";

interface Props {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={clsx("flex gap-3", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div
        className={clsx(
          "shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white",
          isUser ? "bg-gray-600" : "bg-blue-600"
        )}
      >
        {isUser ? <User className="w-4 h-4" /> : <BrainCircuit className="w-4 h-4" />}
      </div>

      {/* Bubble */}
      <div
        className={clsx(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-gray-800 text-white rounded-tr-sm"
            : "bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm"
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.ts && (
          <p className={clsx("text-xs mt-1.5", isUser ? "text-gray-400" : "text-gray-400")}>
            {new Date(message.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </p>
        )}
      </div>
    </div>
  );
}
