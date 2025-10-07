# Documentação de langsmith

## Fonte: https://docs.langchain.com/langsmith

is a platform for building production-grade LLM applications. Monitor and evaluate your application, so you can ship quickly and with confidence.


---

## Fonte: https://docs.smith.langchain.com/reference/js

LangSmith helps you and your team develop and evaluate language models and intelligent agents. It is compatible with any LLM Application and provides seamless integration with , a widely recognized open-source framework that simplifies the process for developers to create powerful language model applications.
> : You can enjoy the benefits of LangSmith without using the LangChain open-source packages! To get started with your own proprietary framework, set up your account and then skip to .
Sign up for using your GitHub, Discord accounts, or an email address and password. If you sign up with an email, make sure to verify your email address before logging in.
```


```

> Projects are groups of traces. All runs are logged to a project. If not specified, the project is set to .
You can still use the LangSmith development platform without depending on any LangChain code. You can connect either by setting the appropriate environment variables, or by directly specifying the connection information in the RunTree.
```


```

Langsmith's wrapper function makes it easy to trace any function or LLM call in your own favorite framework. Below are some examples.
After that, initialize your OpenAI client and wrap the client with method to enable tracing for the completions and chat completions methods:
Note the use of to preserve the function's context. The field in the extra config object marks the function as an LLM call, and enables token usage tracking for OpenAI.
Oftentimes, you use the OpenAI client inside of other functions or as part of a longer sequence. You can automatically get nested traces by using this wrapped method within other functions wrapped with .
```
"The sky appears blue because of a phenomenon known as Rayleigh scattering. The Earth's atmosphere is composed of tiny molecules, such as nitrogen and oxygen, which are much smaller than the wavelength of visible light. When sunlight interacts with these molecules, it gets scattered in all directions. However, shorter wavelengths of light (blue and violet) are scattered more compared to longer wavelengths (red, orange, and yellow). As a result, when sunlight passes through the Earth's atmosphere, the blue and violet wavelengths are scattered in all directions, making the sky appear blue. This scattering of shorter wavelengths is also responsible for the vibrant colors observed during sunrise and sunset, when the sunlight has to pass through a thicker portion of the atmosphere, causing the longer wavelengths to dominate the scattered light."

```

One neat trick you can use for Next.js and other similar server frameworks is to wrap the entire exported handler for a route to group traces for the any sub-runs. Here's an example:
The contains integrations with a variety of model providers. Here's an example of how you can trace outputs in a Next.js handler:
```


```

Do note that this will trace ALL methods in the SDK, not just chat completion endpoints. If the SDK you are wrapping has other methods, we recommend using it for only LLM calls.
A RunTree tracks your application. Each RunTree object is required to have a name and run_type. These and other important attributes are as follows:

```


```

Once your runs are stored in LangSmith, you can convert them into a dataset. For this example, we will do so using the Client, but you can also do this using the web interface, as explained in the .
```


```



---

## Fonte: https://docs.langchain.com/langsmith/administration-overview



An organization is a logical grouping of users within LangSmith with its own billing configuration. Typically, there is one organization per company. An organization can have multiple workspaces. For more details, see the . When you log in for the first time, a personal organization will be created for you automatically. If you’d like to collaborate with others, you can create a separate organization and invite your team members to join. There are a few important differences between your personal organization and shared organizations:
Workspaces were formerly called Tenants. Some code and APIs may still reference the old name for a period of time during the transition.
A workspace is a logical grouping of users and resources within an organization. A workspace separates trust boundaries for resources and access control. Users may have permissions in a workspace that grant them access to the resources in that workspace, including tracing projects, datasets, annotation queues, and prompts. For more details, see the . It is recommended to create a separate workspace for each team within your organization. To organize resources even further, you can use to group resources within a workspace. * Data retention settings and usage limits will be available soon for the organization level as well ** Self-hosted installations may enable workspace-level invites of users to the organization via a feature flag. See the for details. Resource tags allow you to organize resources within a workspaces. Each tag is a key-value pair that can be assigned to a resource. Tags can be used to filter workspace-scoped resources in the UI and API: Projects, Datasets, Annotation Queues, Deployments, and Experiments. Each new workspace comes with two default tag keys: and ; as the names suggest, these tags can be used to categorize resources based on the application and environment they belong to. More tags can be added as needed. A user is a person who has access to LangSmith. Users can be members of one or more organizations and workspaces within those organizations.
We ended support for legacy API keys prefixed with on October 22, 2024 in favor of personal access tokens (PATs) and service keys. We require using PATs and service keys for all new integrations. API keys prefixed with will no longer work as of October 22, 2024.
When you create an API key, you have the option to set an expiration date. Adding an expiration date keys enhances security and minimize the risk of unauthorized access. For example, you may set expiration dates on keys for temporary tasks that require elevated access. By default, keys never expire. Once expired, an API key is no longer valid and cannot be reactivated or have its expiration modified. Personal Access Tokens (PATs) are used to authenticate requests to the LangSmith API. They are created by users and scoped to a user. The PAT will have the same permissions as the user that created it. We recommend not using these to authenticate requests from your application, but rather using them for personal scripts or tools that interact with the LangSmith API. If the user associated with the PAT is removed from the organization, the PAT will no longer work. Service keys are similar to PATs, but are used to authenticate requests to the LangSmith API on behalf of a service account. Only admins can create service keys. We recommend using these for applications / services that need to interact with the LangSmith API, such as LangGraph agents or other integrations. Service keys may be scoped to a single workspace, multiple workspaces, or the entire organization, and can be used to authenticate requests to the LangSmith API for whichever workspace(s) it has access to.
  * : You must include the header when accessing workspace-scoped resources. Without it, the request will fail with a error.


Organization roles are distinct from the Enterprise feature (RBAC) below and are used in the context of multiple . Your organization role determines your workspace membership characteristics and your organization-level permissions. See the for more information.
  * grants full access to manage all organization configuration, users, billing, and workspaces. 
  * may read organization information but cannot execute any write actions at the organization level. **An can be added to a subset of workspaces and assigned workspace roles as usual (if RBAC is enabled), which specify permissions at the workspace level.**


The role is only available in organizations on plans with multiple workspaces. In organizations limited to a single workspace, all users are . Custom organization-scoped roles are not available yet.
RBAC (Role-Based Access Control) is a feature that is only available to Enterprise customers. If you are interested in this feature, . Other plans default to using the Admin role for all users.
Roles are used to define the set of permissions that a user has within a workspace. There are three built-in system roles that cannot be edited:

Use to organize resources by environment using the default tag key and different values for the environment (e.g. , , ). This tagging structure will allow you to organize your tracing projects today and easily enforce permissions when we release attribute based access control (ABAC). ABAC on the resource tag will provide a fine-grained way to restrict access to production tracing projects, for example. We do not recommend that you use Workspaces for environment separation as you cannot share resources across Workspaces. If you would like to promote a prompt from to , we recommend you use commit tags instead. See for more information. In May 2024, LangSmith introduced a maximum data retention period on traces of 400 days. In June 2024, LangSmith introduced a new data retention based pricing model where customers can configure a shorter data retention period on traces in exchange for savings up to 10x. On this page, we’ll go through how data retention works and is priced in LangSmith.
  * : Many data privacy regulations, such as GDPR in Europe or CCPA in California, require organizations to delete personal data once it’s no longer necessary for the purposes for which it was collected. Setting retention periods aids in compliance with such regulations.

After the specified retention period, traces are no longer accessible via the runs table or API. All user data associated with the trace (e.g. inputs and outputs) is deleted from our internal systems within a day thereafter. Some metadata associated with each trace may be retained indefinitely for analytics and billing purposes.
Auto upgrades can have an impact on your bill. Please read this section carefully to fully understand your estimated LangSmith tracing costs.
When you use certain features with tier traces, their data retention will be automatically upgraded to tier. This will increase both the retention period, and the cost of the trace.


  1. We think that traces that match any of these conditions are fundamentally more interesting than other traces, and therefore it is good for users to be able to keep them around longer.
  2. We philosophically want to charge customers an order of magnitude lower for traces that may not be interacted with meaningfully. We think auto-upgrades align our pricing model with the value that LangSmith brings, where only traces with meaningful interaction are charged at a higher rate.

If you have questions or concerns about our pricing model, please feel free to reach out to and let us know your thoughts!
  * : The monitoring tab will continue to work even after a base tier trace’s data retention period ends. It is powered by trace metadata that exists for >30 days, meaning that your monitoring graphs will continue to stay accurate even on tier traces.
  * : Datasets have an indefinite data retention period. Restated differently, if you add a trace’s inputs and outputs to a dataset, they will never be deleted. We suggest that if you are using LangSmith for data collection, you take advantage of the datasets feature.

The first metric includes all traces, regardless of tier. The second metric just counts the number of extended retention traces. A natural question to ask when considering our pricing is why not just show the number of tier and tier traces directly on the invoice? While we understand this would be more straightforward, it doesn’t fit trace upgrades properly. Consider a tier trace that was recorded on June 30, and upgraded to tier on July 3. The tier trace occurred in the June billing period, but the upgrade occurred in the July billing period. Therefore, we need to be able to measure these two events independently to properly bill our customers. If your trace was recorded as an extended retention trace, then the and metrics will both be recorded with the same timestamp. The Base Charge for a trace is .05¢ per trace. We priced the upgrade such that an retention trace costs 10x the price of a base tier trace (.50¢ per trace) including both metrics. Thus, each upgrade costs .45¢. To ensure access and stability, LangSmith will respond with HTTP Status Code 429 indicating that rate or usage limits have been exceeded under the following circumstances: This 429 is the the result of exceeding a fixed number of API calls over a 1 minute window on a per API key/access token basis. The start of the window will vary slightly — it is not guaranteed to start at the start of a clock minute — and may change depending on application deployment events. After the max events are received we will respond with a 429 until 60 seconds from the start of the evaluation window has been reached and then the process repeats. This 429 is thrown by our application load balancer and is a mechanism in place for all LangSmith users independent of plan tier to ensure continuity of service for all users.
The LangSmith SDK takes steps to minimize the likelihood of reaching these limits on run-related endpoints by batching up to 100 runs from a single session ID into a single API call.
This 429 is the result of reaching your maximum hourly events ingested and is evaluated in a fixed window starting at the beginning of each clock hour in UTC and resets at the top of each new hour. An event in this context is the creation or update of a run. So if run is created, then subsequently updated in the same hourly window, that will count as 2 events against this limit. This is thrown by our application and varies by plan tier, with organizations on our Startup/Plus and Enterprise plan tiers having higher hourly limits than our Free and Developer Plan Tiers which are designed for personal use. This 429 is the result of reaching the maximum amount of data ingested across your trace inputs, outputs, and metadata and is evaluated in a fixed window starting at the beginning of each clock hour in UTC and resets at the top of each new hour. Typically, inputs, outputs, and metadata are send on both run creation and update events. So if a run is created and is 2.0MB in size at creation, and 3.0MB in size when updated in the same hourly window, that will count as 5.0MB of storage against this limit. This is thrown by our application and varies by plan tier, with organizations on our Startup/Plus and Enterprise plan tiers having higher hourly limits than our Free and Developer Plan Tiers which are designed for personal use. This 429 is the result of reaching your maximum monthly traces ingested and is evaluated in a fixed window starting at the beginning of each calendar month in UTC and resets at the beginning of each new month. This is thrown by our application and applies only to the Developer Plan Tier when there is no payment method on file. This 429 is the result of reaching your usage limit as configured by your organization admin and is evaluated in a fixed window starting at the beginning of each calendar month in UTC and resets at the beginning of each new month. Since some 429 responses are temporary and may succeed on a successive call, if you are directly calling the LangSmith API in your application we recommend implementing retry logic with exponential backoff and jitter.
It is important to note that if you are saturating the endpoints for extended periods of time, retries may not be effective as your application will eventually run large enough backlogs to exhaust all retries.If that is the case, we would like to discuss your needs more specifically. Please reach out to with details about your applications throughput needs and sample code and we can work with you to better understand whether the best approach is fixing a bug, changes to your application code, or a different LangSmith plan.
LangSmith lets you configure usage limits on tracing. Note that these are limits, not limits, which mean they let you limit the quantity of occurrences of some event rather than the total amount you will spend. Usage limiting is approximate, meaning that we do not guarantee the exactness of the limit. In rare cases, there may be a small period of time where additional traces are processed above the limit threshold before usage limiting begins to apply. The extended data retention traces limit has side effects. If the limit is already reached, any feature that could cause an auto-upgrade of tracing tiers becomes inaccessible. This is because an auto-upgrade of a trace would cause another extended retention trace to be created, which in turn should not be allowed by the limit. Therefore, you can no longer: Usage limits can be updated from the page under . Limit values are cached, so it may take a minute or two before the new limits apply.


---

## Fonte: https://python.langchain.com

These docs will be deprecated and no longer maintained with the release of LangChain v1.0 in October 2025. 


LangChain implements a standard interface for large language models and related technologies, such as embedding models and vector stores, and integrates with hundreds of providers. See the page for more.
  * (e.g. , , etc.): Important integrations have been split into lightweight packages that are co-maintained by the LangChain team and the integration developers.


If you're looking to build something specific or are more of a hands-on learner, check out our . This is the best place to get started.
Explore the full list of LangChain tutorials , and check out other . To learn more about LangGraph, check out our first LangChain Academy course, , available .
you’ll find short answers to “How do I….?” types of questions. These how-to guides don’t cover topics in depth – you’ll find that material in the and the . However, these guides will help you quickly accomplish common tasks using , , and other common LangChain components.
Introductions to all the key parts of LangChain you’ll need to know! you'll find high level explanations of all LangChain concepts.
LangChain is part of a rich ecosystem of tools that integrate with our framework and build on top of it. If you're looking to get up and running quickly with , , or other LangChain components from a specific provider, check out our growing list of .
Build stateful, multi-actor applications with LLMs. Integrates smoothly with LangChain, but can be used without it. LangGraph powers production-grade agents, trusted by LinkedIn, Uber, Klarna, GitLab, and many more.


---

## Fonte: https://docs.langchain.com/langsmith/prompt-engineering-quickstart

Prompts guide the behavior of large language models (LLM). is the process of crafting, testing, and refining the instructions you give to an LLM so it produces reliable and useful responses. LangSmith provides tools to create, version, test, and collaborate on prompts. You’ll also encounter common concepts like , which let you reuse structured prompts, and , which allow you to dynamically insert values (such as a user’s question) into a prompt. In this quickstart, you’ll create, test, and improve prompts using either the UI or the SDK. This quickstart will use OpenAI as the example LLM provider, but the same workflow applies across other providers.


When adding workspace secrets in the LangSmith UI, make sure the secret keys match the environment variable names expected by your model provider.


  1. Set the you want to use. The and you select will determine the parameters that are configurable on this configuration page. Once set, click .
  2. 
LangSmith allows for team-based prompt iteration. members can experiment with prompts in the playground and save their changes as a new when ready.
  *   *     1. Navigate to in the left-hand menu. Select the prompt. Once on the prompt’s detail page, move to the tab. Find the tag icon .


  * Learn how to test your prompt’s performance over a dataset instead of individual examples, refer to .




---

## Fonte: https://docs.langchain.com/langsmith/prompt-engineering



  * : Create promptsthrough the UI or SDK, configure settings, use tools, include multimodal content, and connect to different model providers.




---

## Fonte: https://docs.langchain.com/langsmith/home

is a platform for building production-grade LLM applications. Monitor and evaluate your application, so you can ship quickly and with confidence.


---

## Fonte: https://docs.langchain.com/langsmith/evaluation-quickstart

are a quantitative way to measure the performance of LLM applications. LLMs can behave unpredictably, even small changes to prompts, models, or inputs can significantly affect results. Evaluations provide a structured way to identify failures, compare versions, and build more reliable AI applications.
  * : The part of your application you want to test—this might be a single LLM call with a new prompt, one module, or your entire workflow.

This quickstart guides you through running a starter evaluation that checks the correctness of LLM responses, using either the LangSmith SDK or UI.


When adding workspace secrets in the LangSmith UI, make sure the secret keys match the environment variable names expected by your model provider.
  1. 

  1. Select on the top right to run your evaluation. This will create an with a preview in the table. You can view in full by clicking the experiment name.





---

## Fonte: https://docs.langchain.com/langsmith/observability-quickstart



is a critical requirement for applications built with large language models (LLMs). LLMs are non-deterministic, which means that the same prompt can produce different responses. This behavior makes debugging and monitoring more challenging than with traditional software. LangSmith addresses this by providing end-to-end visibility into how your application handles a request. Each request generates a , which captures the full record of what happened. Within a trace are individual , the specific operations your application performed, such as an LLM call or a retrieval step. Tracing runs allows you to inspect, debug, and validate your application’s behavior.


The example app in this quickstart will use OpenAI as the LLM provider. You can adapt the example for your app’s LLM provider.
If you’re building an application with or , you can enable LangSmith tracing with a single environment variable. Get started by reading the guides for tracing with or tracing with .

You can use the example app code outlined in this step to instrument a RAG application. Or, you can use your own application code that includes an LLM call. This is a minimal RAG app that uses the OpenAI SDK directly without any LangSmith tracing added yet. It has three main parts:
  * : Combines the retrieved documents with the user’s question to form a system prompt, calls the endpoint with , and returns the assistant’s response.


```
























```

This snippet wraps the OpenAI client so that every subsequent model call is logged automatically as a traced child run in LangSmith.
  1. ```






















```

  2. In the , navigate to the Tracing Project for your workspace (or the workspace you specified in ). You’ll see the OpenAI call you just instrumented.


  1. ```
























```

  2. Return to the , navigate to the Tracing Project for your workspace (or the workspace you specified in ). You’ll find a trace of the entire app pipeline with the step and the LLM call.





---

## Fonte: https://docs.langchain.com/oss/python

LangChain is the easiest way to start building with LLMs, letting you get started on building agents with OpenAI, Anthropic, Google, and in under 10 lines of code. LangChain are built on top of in order to provide durable execution, streaming, human-in-the-loop, persistence, and more. You do not need to know LangGraph for basic LangChain agent usage.
```















```

[ Different providers have unique APIs for interacting with models, including the format of responses. LangChain standardizes how you interact with models so that you can seamlessly swap providers and avoid lock-in. ](https://docs.langchain.com/oss/python/langchain/models)[ LangChain’s agent abstraction is designed to be easy to get started with, letting you build a simple agent in under 10 lines of code. But it also provides enough flexibility to allow you to do all the context engineering your heart desires. ](https://docs.langchain.com/oss/python/langchain/agents)[ LangChain’s agents are built on top of LangGraph. This allows us to take advantage of LangGraph’s durable execution, human-in-the-loop support, persistence, and more. ](https://docs.langchain.com/oss/python/langgraph/overview)[ Gain deep visibility into complex agent behavior with visualization tools that trace execution paths, capture state transitions, and provide detailed runtime metrics. ](https://docs.langchain.com/langsmith/home)


---

## Fonte: https://docs.langchain.com/langsmith/pricing-faq

  * [I’ve been using LangSmith since before pricing took effect for new users. When will pricing go into effect for my account?](https://docs.langchain.com/langsmith/pricing-faq#i%E2%80%99ve-been-using-langsmith-since-before-pricing-took-effect-for-new-users-when-will-pricing-go-into-effect-for-my-account%3F)


###  I’ve been using LangSmith since before pricing took effect for new users. When will pricing go into effect for my account?
If you’ve been using LangSmith already, your usage will be billable starting in July 2024. At that point if you want to add seats or use more than the monthly allotment of free traces, you will need to add a credit card to LangSmith or contact sales. If you are interested in the Enterprise plan with higher rate limits and special deployment options, you can learn more or make a purchase by . For teams that want to collaborate in LangSmith, check out the Plus plan. , you may be eligible for our Startup plan with discounted prices and a generous free monthly trace allotment. Please reach out via our for more details. If you need more advanced administration, authentication and authorization, deployment options, support, or annual invoicing, the Enterprise plan is right for you. Please reach out via our for more details. A seat is a distinct user inside your organization. We consider the total number of users (including invited users) to determine the number of seats to bill. A trace is one complete invocation of your application chain or agent, evaluator run, or playground run. Here is an of a single trace.

When you first sign up for a LangSmith account, you get a Personal organization that is limited to 5000 monthly traces. To continue sending traces after reaching this limit, upgrade to the Developer or Plus plans by adding a credit card. Head to to upgrade. Similarly, if you’ve hit the rate limits on your current plan, you can upgrade to a higher plan to get higher limits, or reach out to with questions. Yes, Developer plan users can easily upgrade to the Plus plan on the page. For the Enterprise plan, please to discuss your needs. Seats are billed monthly on the first of the month. Additional seats purchased mid-month are pro-rated and billed within one day of the purchase. Seats removed mid-month will not be credited. As long as you have a card on file in your account, we’ll service your traces and bill you on the first of the month for traces that you submitted in the previous month. You will be able to set usage limits if you so choose to limit the maximum charges you could incur in any given month. You can set limits on the number of traces that can be sent to LangSmith per month on the page.
While we do show you the dollar value of your usage limit for convenience, this limit evaluated in terms of number of traces instead of dollar amount. For example, if you are approved for our startup plan tier where you are given a generous allotment of free traces, your usage limit will not automatically change.
Under the Settings section for your Organization you will see subsection for . There, you will be able to see a graph of the daily number of billable LangSmith traces from the last 30, 60, or 90 days. Note that this data is delayed by 1-2 hours and so may trail your actual number of runs slightly for the current day. Customers on the Developer and Plus plan tiers should email . Customers on the Enterprise plan should contact their sales representative directly. On the Plus plan, you will also receive preferential, email support at for LangSmith-related questions only and we’ll do our best to respond within the next business day. On the Enterprise plan, you’ll get white-glove support with a Slack channel, a dedicated customer success manager, and monthly check-ins to go over LangSmith and LangChain questions. We can help with anything from debugging, agent and RAG techniques, evaluation approaches, and cognitive architecture reviews. If you purchase the add-on to run LangSmith in your environment, we’ll also support deployments and new releases with our infra engineering team on-call. You may choose to sign up in either the US or EU region. See the for more details. If you’re on the Enterprise plan, we can deliver LangSmith to run on your kubernetes cluster in AWS, GCP, or Azure so that data never leaves your environment. You can request more information about our security policies and posture at . Please note we only enter into BAAs with customers on our Enterprise plan. We will not train on your data, and you own all rights to your data. See for more information.


---

## Fonte: https://docs.langchain.com/langsmith/observability

Welcome to the LangSmith Observability documentation. The following sections help you set up and use tracing, monitoring, and observability features:




---

## Fonte: https://docs.langchain.com/langsmith/architectural-overview







Self-hosted LangSmith is an add-on to the Enterprise Plan designed for our largest, most security-conscious customers. See our for more detail, and if you want to get a license key to trial LangSmith in your environment.
You can run LangSmith in Kubernetes (recommended) or Docker in a cloud environment that you control. The LangSmith application consists of several components including LangSmith servers and stateful services: To access the LangSmith UI and send API requests, you will need to expose the service. Depending on your installation method, this can be a load balancer or a port exposed on the host machine.
LangSmith Self-Hosted will bundle all storage services by default. You can configure LangSmith to use external versions of all storage services. In a production setting, we .
is a powerful, open source object-relational database system that uses and extends the SQL language combined with many features that safely store and scale the most complicated data workloads LangSmith uses PostgreSQL as the primary data store for transactional workloads and operational data (almost everything besides traces and feedback). is a powerful in-memory key-value database that persists on disk. By holding data in memory, Redis offers high performance for operations like caching. LangSmith uses blob storage to store large files, such as trace artifacts, feedback attachments, and other large data objects. Blob storage is optional, but highly recommended for production deployments. The frontend uses Nginx to serve the LangSmith UI and route API requests to the other servers. This serves as the entrypoint for the application and is the only component that must be exposed to users. The backend is the main entrypoint for CRUD API requests and handles the majority of the business logic for the application. This includes handling requests from the frontend and SDK, preparing traces for ingestion, and supporting the hub API. The queue handles incoming traces and feedback to ensure that they are ingested and persisted into the traces and feedback datastore asynchronously, handling checks for data integrity and ensuring successful insert into the datastore, handling retries in situations such as database errors or the temporary inability to connect to the database. The playground is a service that handles forwarding requests to various LLM APIs to support the LangSmith Playground feature. This can also be used to connect to your own custom model servers. The ACE backend is a service that handles executing arbitrary code in a secure environment. This is used to support running custom code within LangSmith.


---

## Fonte: https://api.smith.langchain.com/redoc

  *   *   *   *   *   *   *   *   *   *   *   *   *   * 

Given a session, a number K, and (optionally) a list of metadata keys, return the top K values for each key.
Enum for payment plans that the user can change to. Developer plans are permanent and enterprise plans will be changed manually.  
---  
Only modifications made on or before this time are included. If None, the latest version of the dataset is used.  
---  
Only modifications made on or before this time are included. If None, the latest version of the dataset is used.  
---  
Only modifications made on or before this time are included. If None, the latest version of the dataset is used.  
---  
This endpoint hard deletes versions of a dataset example(s). Deletion is performed by setting inputs, outputs, and metadata to null and deleting attachment files while keeping the example ID, dataset ID, and creation timestamp. IMPORTANT: attachment files can take up to 7 days to be deleted. inputs, outputs and metadata are nullified immediately.
This endpoint allows clients to upload examples to a specified dataset by sending a multipart/form-data POST request. Each form part contains either JSON-encoded data or binary attachment files associated with an example.
This endpoint allows clients to update existing examples in a specified dataset by sending a multipart/form-data PATCH request. Each form part contains either JSON-encoded data or binary attachment files to update an example.
Only modifications made on or before this time are included. If None, the latest version of the dataset is used.  
---  
Only modifications made on or before this time are included. If None, the latest version of the dataset is used.  
---  
Only modifications made on or before this time are included. If None, the latest version of the dataset is used.  
---  
Only modifications made on or before this time are included. If None, the latest version of the dataset is used.  
---  
Only modifications made on or before this time are included. If None, the latest version of the dataset is used.  
---  
Fetch examples for a dataset, and fetch the runs for each example if they are associated with the given session_ids.
Fetch examples for a dataset, and fetch the runs for each example if they are associated with the given session_ids.
Only modifications made on or before this time are included. If None, the latest version of the dataset is used.  
---  
This method is invoked under the assumption that the run is already visible in the app, thus already present in DB
Only modifications made on or before this time are included. If None, the latest version of the dataset is used.  
---  
Only modifications made on or before this time are included. If None, the latest version of the dataset is used.  
---  
AIMessage (object) or HumanMessage (object) or ChatMessage (object) or SystemMessage (object) or FunctionMessage (object) or ToolMessage (object) or AIMessageChunk (object) or HumanMessageChunk (object) or ChatMessageChunk (object) or SystemMessageChunk (object) or FunctionMessageChunk (object) or ToolMessageChunk (object)  
---  
Retrieves all experiment view override configurations for a specific dataset. This endpoint returns column display overrides including color gradients, precision settings, and column visibility configurations that customize how experiment results are displayed in the UI.


Creates a new experiment view override configuration for a dataset with column display settings. This endpoint allows you to customize how experiment results are displayed by configuring column-specific overrides including colors, precision, and visibility.


Retrieves a specific experiment view override configuration using both dataset ID and override ID. This endpoint provides more precise access to experiment view overrides when you have the specific override ID, useful for direct links or cached references.
Permanently deletes an experiment view override configuration for a dataset. This operation removes all column override settings including color gradients, precision configurations, and visibility settings.
After deletion, the experiment view will revert to default column display settings. This action cannot be undone - you will need to recreate the override configuration if you want to restore custom column settings.
Both the dataset and override must exist and be accessible by the authenticated user. The operation will fail if the override doesn't exist or if the user doesn't have appropriate permissions for the dataset.
This endpoint performs a complete replacement of the column overrides configuration. All existing column overrides will be replaced with the new configuration provided in the request body. To add or modify individual columns, include the complete desired configuration in the request.
Queues a single run for ingestion. The request body must be a JSON-encoded run object that follows the Run schema.
Ingests a batch of runs in a single JSON payload. The payload must have and/or arrays containing run objects. Prefer this endpoint over single‑run ingestion when submitting hundreds of runs, but offers better handling for very large fields and attachments.
  * – arbitrary binary attachment stored in S3. : every part must set either a header or parameter. Per‑part is allowed; the top‑level request may be or . for high‑volume ingestion.


Updates a run identified by its ID. The body should contain only the fields to be changed; unknown fields are ignored.
Creates a new alert rule. The request body must be a JSON-encoded alert rule object that follows the CreateAlertRuleRequest schema.


---

## Fonte: https://www.langchain.com/langsmith

We may use cookies to help you navigate efficiently and perform certain functions. You will find detailed information about all cookies under each consent category below.
The cookies that are categorized as "Necessary" are stored on your browser as they are essential for enabling the basic functionalities of the site.... 
Necessary cookies are required to enable the basic features of this site, such as providing secure log-in or adjusting your consent preferences. These cookies do not store any personally identifiable data.
Functional cookies help perform certain functionalities like sharing the content of the website on social media platforms, collecting feedback, and other third-party features.
Analytical cookies are used to understand how visitors interact with the website. These cookies help provide information on metrics such as the number of visitors, bounce rate, traffic source, etc.
Performance cookies are used to understand and analyze the key performance indexes of the website which helps in delivering a better user experience for the visitors.
Advertisement cookies are used to provide visitors with customized advertisements based on the pages you visited previously and to analyze the effectiveness of the ad campaigns.
Quickly debug and understand non-deterministic LLM app behavior with tracing. See what your agent is doing step by step —then fix issues to improve latency and response quality.
Evaluate your app by saving production traces to datasets — then score performance with LLM-as-Judge evaluators. Gather human feedback from subject-matter experts to assess response relevance, correctness, harmfulness, and other criteria.
Experiment with models and prompts in the Playground, and compare outputs across different prompt versions. Any teammate can use the Prompt Canvas UI to directly recommend and improve prompts. 
Track business-critical metrics like costs, latency, and response quality with live dashboards — then get alerted when problems arise and drill into root cause.
LLM app traces are complex — packed with text, tool calls, audio, and images. You’ll need to find signal in the noise, so you can debug faster and explain behavior with confidence.
There are no guarantees with LLMs. Unified testing & observability lets you turn real user data into evaluation datasets and catch issues that traditional monitoring & testing tools would miss.
From PMs to subject matter experts, everyone’s involved in building GenAI apps. Close the gap between ideas and working software by making it easy to collaborate across teams — whether it’s through writing prompts or providing feedback on experiments.
Yes, you can log traces to LangSmith using a standard OpenTelemetry client to access all LangSmith features, including tracing, running evals, and prompt engineering. 
LangSmith traces contain the full information of all the inputs and outputs of each step of the application, giving users full visibility into their agent or LLM app behavior. LangSmith also allows users to instantly run evals to assess agent or LLM app performance — including LLM-as-Judge evaluators for auto-scoring and the ability to attach human feedback. 
Yes, we allow customers to self-host LangSmith on our enterprise plan. We deliver the software to run on your Kubernetes cluster, and data will not leave your environment. For more information, check out our .
No, LangSmith does not add any latency to your application. In the LangSmith SDK, there’s a callback handler that sends traces to a LangSmith trace collector which runs as an async, distributed process. Additionally, if LangSmith experiences an incident, your application performance will not be disrupted.
We will not train on your data, and you own all rights to your data. See LangSmith for more information.


---

## Fonte: https://langchain.com/pricing

We may use cookies to help you navigate efficiently and perform certain functions. You will find detailed information about all cookies under each consent category below.
The cookies that are categorized as "Necessary" are stored on your browser as they are essential for enabling the basic functionalities of the site.... 
Necessary cookies are required to enable the basic features of this site, such as providing secure log-in or adjusting your consent preferences. These cookies do not store any personally identifiable data.
Functional cookies help perform certain functionalities like sharing the content of the website on social media platforms, collecting feedback, and other third-party features.
Analytical cookies are used to understand how visitors interact with the website. These cookies help provide information on metrics such as the number of visitors, bounce rate, traffic source, etc.
Performance cookies are used to understand and analyze the key performance indexes of the website which helps in delivering a better user experience for the visitors.
Advertisement cookies are used to provide visitors with customized advertisements based on the pages you visited previously and to analyze the effectiveness of the ad campaigns.
Our Developer plan is a great choice for personal projects. You will have 1 free seat with access to LangSmith (5k base traces/month included). 
The Plus plan is for teams that want to self-serve with moderate usage and collaboration needs. You can purchase up to 10 seats with access to LangSmith (10k base traces/month included). You will be able to ship agents with our managed LangGraph Platform Cloud service, with 1 free dev-sized deployment included. 
The Enterprise plan is for teams that need more advanced administration, security, support, or deployment options. to learn more.
Yes! We offer a Startup Plan for LangSmith, designed for early-stage companies building agentic applications. You’ll get discounted rates and generous free trace allotments to build with confidence from day one.
‍ to get started with startup pricing. Customers can stay on the Startup Plan for 2 years before graduating to the Plus Plan.
For the Developer or Plus Plan, seats are billed monthly on the 1st or pro-rated if added mid-month (no credit for removed seats); traces are billed monthly in arrears for your usage. Enterprise plans are invoiced annually upfront.
We will not train on your data, and you own all rights to your data. See our for more information.
A trace represents a single execution of your application—whether it’s an agent, evaluator, or playground session. It can include many individual steps, such as LLM calls and other tracked events. Here's an of a single trace.
Base traces have a shorter retention period of 14 days and cost $0.50 per 1k traces. Extended traces have a longer retention period of 400 days and cost $5.00 per 1k traces. You can "upgrade" base traces to extended traces at $4.50 per 1k traces.
Base traces are short-lived (14-day retention) and ideal for quick debugging or ad-hoc analysis. They’re priced for volume and short-term utility.
Extended traces, on the other hand, are retained for 400 days and often include valuable feedback—whether from users, evaluators, or human labelers. This feedback makes them essential for ongoing improvement and model tuning (higher utility), which comes with a higher price point.
Base traces are short-lived (14-day retention) and ideal for quick debugging or ad-hoc analysis. They’re priced for volume and short-term utility.
Extended traces, on the other hand, are retained for 400 days and often include valuable feedback—whether from users, evaluators, or human labelers. This feedback makes them essential for ongoing improvement and model tuning (higher utility), which comes with a higher price point.
If you’ve used up your free traces, you can input your credit card details on the Developer or Plus plans to continue sending traces to LangSmith. If you’ve hit the performance usage limits on your tier, you can upgrade to a higher plan to get better limits, or reach out to support@langchain.dev with questions.
Plus plans include 1 free dev-sized deployment. If you spin up additional dev-sized or production-sized deployments, you’ll be charged by usage (nodes executed and uptime).
If you’re on the Plus plan, you get 1 free dev-sized deployment – all usage in this deployment will be free no matter how many node executions are run.
Nodes Executed is the aggregate number of nodes in a LangGraph application that are called and completed successfully during an invocation of the application. If a node in the graph is not called during execution or ends in an error state, these nodes will not be counted. If a node is called and completes successfully multiple times, each occurrence will be counted.
Uptime is the duration your deployment’s database is live and persisting state. Uptime will be tracked as soon as your deployment is live and ends when you shut it down. Dev deployments are typically short-lived (used during iteration, then deleted) – whereas Production deployments stay live and are updated via revisions (rather than being deleted). 
We recommend using the production-sized deployment for any customer-facing agent. Dev-sized deployments are intended for testing and do not support horizontal scaling, backups, or performance optimizations needed in production.


---

