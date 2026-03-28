# Sampling Parameters — vLLM
Contents
--------

*   `SamplingParams`
    *   `SamplingParams.clone()`
    *   `SamplingParams.update_from_generation_config()`

Sampling Parameters#
------------------------------------------------------------------------

_class_ vllm.SamplingParams(_n: int \= 1_, _best\_of: int | None \= None_, _\_real\_n: int | None \= None_, _presence\_penalty: float \= 0.0_, _frequency\_penalty: float \= 0.0_, _repetition\_penalty: float \= 1.0_, _temperature: float \= 1.0_, _top\_p: float \= 1.0_, _top\_k: int \= \-1_, _min\_p: float \= 0.0_, _seed: int | None \= None_, _stop: ~typing.List\[str\] | str | None \= None_, _stop\_token\_ids: ~typing.List\[int\] | None \= None_, _bad\_words: ~typing.List\[str\] | None \= None_, _ignore\_eos: bool \= False_, _max\_tokens: int | None \= 16_, _min\_tokens: int \= 0_, _logprobs: int | None \= None_, _prompt\_logprobs: int | None \= None_, _detokenize: bool \= True_, _skip\_special\_tokens: bool \= True_, _spaces\_between\_special\_tokens: bool \= True_, _logits\_processors: ~typing.Any | None \= None_, _include\_stop\_str\_in\_output: bool \= False_, _truncate\_prompt\_tokens: int | None \= None_, _output\_kind: ~vllm.sampling\_params.RequestOutputKind \= RequestOutputKind.CUMULATIVE_, _output\_text\_buffer\_length: int \= 0_, _\_all\_stop\_token\_ids: ~typing.Set\[int\] \= <factory>_, _guided\_decoding: ~vllm.sampling\_params.GuidedDecodingParams | None \= None_, _logit\_bias: ~typing.Dict\[int_, _float\] | None \= None_, _allowed\_token\_ids: ~typing.List\[int\] | None \= None_)
\[source\]
#

Sampling parameters for text generation.

Overall, we follow the sampling parameters from the OpenAI text completion API (https://platform.openai.com/docs/api-reference/completions/create). In addition, we support beam search, which is not supported by OpenAI.

Parameters:

*   **n** – Number of output sequences to return for the given prompt.
    
*   **best\_of** – Number of output sequences that are generated from the prompt. From these best\_of sequences, the top n sequences are returned. best\_of must be greater than or equal to n. By default, best\_of is set to n.
    
*   **presence\_penalty** – Float that penalizes new tokens based on whether they appear in the generated text so far. Values > 0 encourage the model to use new tokens, while values < 0 encourage the model to repeat tokens.
    
*   **frequency\_penalty** – Float that penalizes new tokens based on their frequency in the generated text so far. Values > 0 encourage the model to use new tokens, while values < 0 encourage the model to repeat tokens.
    
*   **repetition\_penalty** – Float that penalizes new tokens based on whether they appear in the prompt and the generated text so far. Values > 1 encourage the model to use new tokens, while values < 1 encourage the model to repeat tokens.
    
*   **temperature** – Float that controls the randomness of the sampling. Lower values make the model more deterministic, while higher values make the model more random. Zero means greedy sampling.
    
*   **top\_p** – Float that controls the cumulative probability of the top tokens to consider. Must be in (0, 1\]. Set to 1 to consider all tokens.
    
*   **top\_k** – Integer that controls the number of top tokens to consider. Set to -1 to consider all tokens.
    
*   **min\_p** – Float that represents the minimum probability for a token to be considered, relative to the probability of the most likely token. Must be in \[0, 1\]. Set to 0 to disable this.
    
*   **seed** – Random seed to use for the generation.
    
*   **stop** – List of strings that stop the generation when they are generated. The returned output will not contain the stop strings.
    
*   **stop\_token\_ids** – List of tokens that stop the generation when they are generated. The returned output will contain the stop tokens unless the stop tokens are special tokens.
    
*   **bad\_words** – List of words that are not allowed to be generated. More precisely, only the last token of a corresponding token sequence is not allowed when the next generated token can complete the sequence.
    
*   **include\_stop\_str\_in\_output** – Whether to include the stop strings in output text. Defaults to False.
    
*   **ignore\_eos** – Whether to ignore the EOS token and continue generating tokens after the EOS token is generated.
    
*   **max\_tokens** – Maximum number of tokens to generate per output sequence.
    
*   **min\_tokens** – Minimum number of tokens to generate per output sequence before EOS or stop\_token\_ids can be generated
    
*   **logprobs** – Number of log probabilities to return per output token. When set to None, no probability is returned. If set to a non-None value, the result includes the log probabilities of the specified number of most likely tokens, as well as the chosen tokens. Note that the implementation follows the OpenAI API: The API will always return the log probability of the sampled token, so there may be up to logprobs+1 elements in the response.
    
*   **prompt\_logprobs** – Number of log probabilities to return per prompt token.
    
*   **detokenize** – Whether to detokenize the output. Defaults to True.
    
*   **skip\_special\_tokens** – Whether to skip special tokens in the output.
    
*   **spaces\_between\_special\_tokens** – Whether to add spaces between special tokens in the output. Defaults to True.
    
*   **logits\_processors** – List of functions that modify logits based on previously generated tokens, and optionally prompt tokens as a first argument.
    
*   **truncate\_prompt\_tokens** – If set to an integer k, will use only the last k tokens from the prompt (i.e., left truncation). Defaults to None (i.e., no truncation).
    
*   **guided\_decoding** – If provided, the engine will construct a guided decoding logits processor from these parameters. Defaults to None.
    
*   **logit\_bias** – If provided, the engine will construct a logits processor that applies these logit biases. Defaults to None.
    
*   **allowed\_token\_ids** – If provided, the engine will construct a logits processor which only retains scores for the given token ids. Defaults to None.
    

clone() → SamplingParams
\[source\]
#

Deep copy excluding LogitsProcessor objects.

LogitsProcessor objects are excluded because they may contain an arbitrary, nontrivial amount of data. See vllm-project/vllm#3087

update\_from\_generation\_config(_generation\_config: Dict")\str"), Any")\]_, _model\_eos\_token\_id: int") | None") \= None_) → None")
\[source\]
#

Update if there are non-default values from generation\_config