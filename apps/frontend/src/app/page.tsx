"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { Send, Upload, FileText, AlertTriangle, Loader2, Info, PlusCircle, LogOut, ThumbsUp, ThumbsDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";

import { 
  askQuery, uploadDocument, getJobStatus, Citation, 
  setApiKey, setJwtToken, getSessions, getSessionMessages,
  SessionResponse, addFeedback, FeedbackResponse
} from "@/lib/api";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  metadata?: any;
  isStreaming?: boolean;
  isSafetyViolation?: boolean;
  feedback?: FeedbackResponse | null;
};

export default function Home() {
  const router = useRouter();
  
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [apiKey, setApiKeyState] = useState("");
  const [isLoaded, setIsLoaded] = useState(false);
  
  // Document Upload State
  const [file, setFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "processing" | "success" | "error">("idle");

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Auth and initial load
  useEffect(() => {
    const token = localStorage.getItem("jwt_token");
    const savedApiKey = localStorage.getItem("ekc_api_key");
    
    if (token) {
      setJwtToken(token);
    } else if (savedApiKey) {
      setApiKey(savedApiKey);
      setApiKeyState(savedApiKey);
    } else {
      router.push("/login");
      return;
    }

    loadSessions();
    setIsLoaded(true);
  }, [router]);

  const loadSessions = async () => {
    try {
      const data = await getSessions();
      setSessions(data);
    } catch (e) {
      console.error("Failed to load sessions", e);
    }
  };

  const loadSessionHistory = async (sessionId: string) => {
    try {
      setCurrentSessionId(sessionId);
      const data = await getSessionMessages(sessionId);
      setMessages(data.map(m => ({
        id: m.id,
        role: m.role as "user" | "assistant",
        content: m.content,
        citations: m.citations,
        feedback: m.feedback
      })));
    } catch (e) {
      console.error("Failed to load session messages", e);
    }
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
  };

  const handleLogout = () => {
    localStorage.removeItem("jwt_token");
    localStorage.removeItem("ekc_api_key");
    setJwtToken("");
    setApiKey("");
    router.push("/login");
  };

  const handleApiKeyChange = (val: string) => {
    setApiKeyState(val);
    setApiKey(val);
    localStorage.setItem("ekc_api_key", val);
  };

  const handleSend = async () => {
    if (!query.trim() || isProcessing) return;

    const userMessage: Message = { id: Date.now().toString(), role: "user", content: query };
    const assistantId = (Date.now() + 1).toString();
    const assistantMessage: Message = { id: assistantId, role: "assistant", content: "", isStreaming: true };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setQuery("");
    setIsProcessing(true);

    try {
      const response = await askQuery({ 
        query: userMessage.content, 
        limit: 5, 
        rerank: true,
        session_id: currentSessionId || undefined
      });
      
      if (response.session_id && !currentSessionId) {
        setCurrentSessionId(response.session_id);
        loadSessions(); // refresh sidebar
      }

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, id: response.message_id || m.id, content: response.answer, citations: response.citations, metadata: response.metadata, isStreaming: false }
            : m
        )
      );
      setIsProcessing(false);
    } catch (err: any) {
      console.error(err);
      const errorMsg = err.message || String(err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: `Error: ${errorMsg}`,
                isStreaming: false,
                isSafetyViolation: errorMsg.includes("POLICY_VIOLATION"),
              }
            : m
        )
      );
      setIsProcessing(false);
    }
  };

  const handleFeedback = async (messageId: string, rating: "up" | "down") => {
    if (!currentSessionId) return;
    try {
      const fb = await addFeedback(messageId, { session_id: currentSessionId, rating });
      setMessages(prev => prev.map(m => 
        m.id === messageId ? { ...m, feedback: fb } : m
      ));
    } catch (e) {
      console.error("Failed to submit feedback", e);
    }
  };

  const handleFileUpload = async () => {
    if (!file) return;
    setUploadStatus("uploading");
    try {
      const res = await uploadDocument(file, "general", "markdown");
      setUploadStatus("processing");
      
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await getJobStatus(res.job_id);
          if (statusRes.status === "completed") {
            setUploadStatus("success");
            clearInterval(pollInterval);
            setTimeout(() => setUploadStatus("idle"), 5000);
          } else if (statusRes.status === "failed") {
            setUploadStatus("error");
            clearInterval(pollInterval);
            setTimeout(() => setUploadStatus("idle"), 5000);
          }
        } catch (e) {
          console.error("Polling failed", e);
        }
      }, 2000);
      
      setFile(null);
    } catch (error) {
      console.error("Upload failed", error);
      setUploadStatus("error");
    }
  };

  if (!isLoaded) return <div className="flex h-screen items-center justify-center"><Loader2 className="w-8 h-8 animate-spin" /></div>;

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-slate-950 font-sans">
      
      {/* Sidebar: Upload & History */}
      <div className="w-80 border-r bg-white dark:bg-slate-900 flex flex-col hidden md:flex">
        <div className="p-4 border-b flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
              Knowledge Copilot
            </h1>
            <p className="text-xs text-slate-500 mt-1">Enterprise RAG Assistant</p>
          </div>
          <Button variant="ghost" size="icon" onClick={handleLogout} title="Logout">
            <LogOut className="w-4 h-4 text-slate-500" />
          </Button>
        </div>

        <div className="p-4 border-b space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold block text-slate-500">Programmatic API Key (Optional)</label>
            <Input 
              type="password" 
              placeholder="Provide to use specific permissions" 
              value={apiKey}
              onChange={(e) => handleApiKeyChange(e.target.value)}
              className="text-xs h-8"
            />
          </div>
        </div>

        <div className="p-4 border-b space-y-4">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Upload className="w-4 h-4" /> Add Knowledge
          </h2>
          <Input 
            type="file" 
            accept=".txt,.md" 
            onChange={(e) => setFile(e.target.files?.[0] || null)} 
            className="text-xs"
          />
          <Button 
            onClick={handleFileUpload} 
            disabled={!file || uploadStatus === "uploading" || uploadStatus === "processing"}
            className="w-full text-xs"
            variant="secondary"
          >
            {uploadStatus === "uploading" ? (
              <><Loader2 className="w-3 h-3 mr-2 animate-spin" /> Uploading...</>
            ) : uploadStatus === "processing" ? (
              <><Loader2 className="w-3 h-3 mr-2 animate-spin" /> Processing...</>
            ) : "Upload Document"}
          </Button>
          {uploadStatus === "success" && (
            <p className="text-xs text-green-600">Document successfully indexed!</p>
          )}
          {uploadStatus === "error" && (
            <p className="text-xs text-red-600">Upload or processing failed.</p>
          )}
        </div>

        <div className="flex-1 overflow-auto p-4 flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-sm font-semibold">Chat History</h2>
            <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={handleNewChat}>
              <PlusCircle className="w-3 h-3 mr-1" /> New
            </Button>
          </div>
          <div className="space-y-2 flex-1">
            {sessions.map(s => (
              <div 
                key={s.id} 
                onClick={() => loadSessionHistory(s.id)}
                className={`text-xs truncate p-2 rounded-md cursor-pointer ${
                  currentSessionId === s.id 
                    ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 font-medium" 
                    : "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400"
                }`}
              >
                {s.first_message || "New Chat"}
              </div>
            ))}
            {sessions.length === 0 && (
              <div className="text-xs text-slate-400 italic">No previous chats found.</div>
            )}
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full min-w-0">
        <ScrollArea className="flex-1 min-h-0 p-6" viewportRef={scrollRef}>
          <div className="max-w-4xl mx-auto space-y-6 pb-6">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full mt-32 text-center space-y-4">
                <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center">
                  <Info className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                </div>
                <h2 className="text-2xl font-semibold">How can I help you today?</h2>
                <p className="text-slate-500 max-w-md">
                  Ask me anything about the enterprise corpus. I can synthesize information, compare documents, and provide grounded answers.
                </p>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] ${msg.role === "user" ? "bg-blue-600 text-white rounded-2xl rounded-tr-sm px-5 py-3" : "w-full"}`}>
                    
                    {msg.role === "user" ? (
                      <p className="text-sm">{msg.content}</p>
                    ) : (
                      <div className="space-y-4">
                        {/* Assistant Response Container */}
                        <div className="flex gap-4">
                          <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center shrink-0 mt-1">
                            {msg.isSafetyViolation ? (
                              <AlertTriangle className="w-4 h-4 text-red-600" />
                            ) : (
                              <span className="text-indigo-600 dark:text-indigo-400 font-bold text-xs">AI</span>
                            )}
                          </div>
                          
                          <div className="flex-1 space-y-4">
                            {msg.isSafetyViolation ? (
                              <Alert variant="destructive">
                                <AlertTriangle className="h-4 w-4" />
                                <AlertTitle>Safety Policy Violation</AlertTitle>
                                <AlertDescription>
                                  {msg.content}
                                </AlertDescription>
                              </Alert>
                            ) : (
                              <div className="prose dark:prose-invert max-w-none text-sm leading-relaxed">
                                {msg.content ? (
                                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                                ) : (
                                  <span className="flex items-center gap-2 text-slate-400">
                                    <Loader2 className="w-4 h-4 animate-spin" /> Thinking...
                                  </span>
                                )}
                              </div>
                            )}

                            {/* Citations & Metadata */}
                            {!msg.isStreaming && !msg.isSafetyViolation && (msg.citations?.length || msg.metadata) && (
                              <Accordion type="single" collapsible className="w-full mt-4 border rounded-xl overflow-hidden bg-white dark:bg-slate-900">
                                <AccordionItem value="diagnostics" className="border-none">
                                  <AccordionTrigger className="px-4 py-2 hover:no-underline hover:bg-slate-50 dark:hover:bg-slate-800 text-xs text-slate-500">
                                    <div className="flex items-center gap-4">
                                      <span>{msg.citations?.length || 0} sources retrieved</span>
                                      {msg.metadata?.processing_time_ms && (
                                        <Badge variant="secondary" className="font-normal">
                                          {msg.metadata.processing_time_ms}ms
                                        </Badge>
                                      )}
                                      {msg.metadata?.trace_id && (
                                        <Badge variant="outline" className="font-normal font-mono text-[10px]">
                                          {msg.metadata.trace_id.substring(0,8)}
                                        </Badge>
                                      )}
                                    </div>
                                  </AccordionTrigger>
                                  <AccordionContent className="px-4 py-4 border-t bg-slate-50 dark:bg-slate-900/50">
                                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                      {msg.citations?.map((cit) => (
                                        <Card key={cit.id} className="bg-white dark:bg-slate-950 shadow-sm">
                                          <CardHeader className="p-3 pb-2">
                                            <CardTitle className="text-xs font-mono text-indigo-600 truncate">
                                              <FileText className="w-3 h-3 inline mr-1" />
                                              {cit.source}
                                            </CardTitle>
                                          </CardHeader>
                                          <CardContent className="p-3 pt-0">
                                            <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-4">
                                              {cit.snippet}
                                            </p>
                                          </CardContent>
                                        </Card>
                                      ))}
                                    </div>
                                  </AccordionContent>
                                </AccordionItem>
                              </Accordion>
                            )}
                            
                            {/* Feedback Actions */}
                            {!msg.isStreaming && !msg.isSafetyViolation && msg.content && (
                              <div className="flex items-center gap-2 mt-2 pt-2 border-t dark:border-slate-800">
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  className={`h-7 px-2 text-xs ${msg.feedback?.rating === 'up' ? 'text-green-600 bg-green-50 dark:bg-green-900/20' : 'text-slate-400 hover:text-green-600'}`}
                                  onClick={() => handleFeedback(msg.id, 'up')}
                                  title="Good response"
                                >
                                  <ThumbsUp className={`w-3 h-3 mr-1 ${msg.feedback?.rating === 'up' ? 'fill-current' : ''}`} />
                                  Helpful
                                </Button>
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  className={`h-7 px-2 text-xs ${msg.feedback?.rating === 'down' ? 'text-red-600 bg-red-50 dark:bg-red-900/20' : 'text-slate-400 hover:text-red-600'}`}
                                  onClick={() => handleFeedback(msg.id, 'down')}
                                  title="Poor response"
                                >
                                  <ThumbsDown className={`w-3 h-3 mr-1 ${msg.feedback?.rating === 'down' ? 'fill-current' : ''}`} />
                                  Not Helpful
                                </Button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="p-4 bg-white dark:bg-slate-950 shrink-0 border-t">
          <div className="max-w-4xl mx-auto">
            <div className="relative shadow-lg rounded-2xl bg-white dark:bg-slate-900 border overflow-hidden focus-within:ring-2 ring-indigo-500 ring-offset-2 dark:ring-offset-slate-950 transition-all">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Ask about your enterprise knowledge..."
                className="w-full h-14 pl-4 pr-14 border-0 focus-visible:ring-0 bg-transparent text-sm"
                disabled={isProcessing}
              />
              <Button 
                onClick={handleSend}
                disabled={!query.trim() || isProcessing}
                size="icon"
                className="absolute right-2 top-2 h-10 w-10 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white transition-transform active:scale-95"
              >
                {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </Button>
            </div>
            <div className="text-center mt-2">
              <p className="text-[10px] text-slate-400">
                AI may produce inaccurate information. Responses are filtered by enterprise safety guardrails.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
