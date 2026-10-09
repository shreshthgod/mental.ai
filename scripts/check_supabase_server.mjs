// Configuration/import smoke only. No token verification, account or network.
let requests=0;
const originalFetch=globalThis.fetch;
globalThis.fetch=async()=>{requests++;throw new Error("Unexpected network during SDK configuration check");};
try{
  const {withSupabase,createSupabaseContext}=await import("@supabase/server");
  const {resolveEnv}=await import("@supabase/server/core");
  if(typeof withSupabase!=="function"||typeof createSupabaseContext!=="function")throw new Error("Server SDK exports unavailable");
  const result=resolveEnv();
  if(result.error||!result.data)throw new Error("Server SDK configuration unavailable; check backend environment");
  const data=result.data;
  if(data.url!==process.env.SUPABASE_URL)throw new Error("Server SDK project does not match backend configuration");
  if(data.publishableKeys.default!==process.env.SUPABASE_PUBLISHABLE_KEY)throw new Error("Publishable key could not be resolved");
  if(data.secretKeys.default!==process.env.SUPABASE_SECRET_KEY)throw new Error("Backend key could not be resolved");
  if(!(data.jwks instanceof URL)||data.jwks.href!==process.env.SUPABASE_JWKS_URL)throw new Error("JWKS URL could not be resolved");
  if(requests!==0)throw new Error("Unexpected network request");
  console.log(JSON.stringify({status:"PASSED",server_exports:true,configured_variables:["SUPABASE_URL","SUPABASE_PUBLISHABLE_KEY","SUPABASE_SECRET_KEY","SUPABASE_JWKS_URL"],observed_fetch_calls:requests,authenticated_identity_verified:false,secret_values_printed:false}));
}finally{globalThis.fetch=originalFetch;}
