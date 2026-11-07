// The same archive works under any GitHub account and repository name.
if(location.hostname.endsWith(".github.io")){
  const owner=location.hostname.slice(0,-".github.io".length);
  const folder=location.pathname.split("/").filter(Boolean)[0];
  const repo=folder&&folder!=="index.html"?folder:location.hostname;
  const link=document.getElementById("repository");
  link.href="https://github.com/"+encodeURIComponent(owner)+"/"+encodeURIComponent(repo);
  link.hidden=false;
}
