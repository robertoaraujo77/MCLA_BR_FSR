using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Microsoft.Win32;

namespace MclaBrFsrSetup {
 static class ModernLauncher {
  public static Window Create() {
   using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("MclaSetup.Launcher.xaml")) {
    var window=(Window)XamlReader.Load(stream);window.Tag=new LauncherController(window);return window;
   }
  }
 }
 sealed class LauncherController {
  readonly Window ui;
  readonly Dictionary<string,ComboBox> choices=new Dictionary<string,ComboBox>();
  readonly Dictionary<string,CheckBox> toggles=new Dictionary<string,CheckBox>();
  readonly JavaScriptSerializer json=new JavaScriptSerializer();
  readonly string preferences=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"MCLA_LA_Recompiled","launcher.json");
  bool HasBundle {get{return Assembly.GetExecutingAssembly().GetManifestResourceNames().Contains("MclaSetup.offline.bundle.zip");}}
  string installed;
  Dictionary<string,string> firstRun;
  bool working;
  bool loading;
  Process worker;
  T Find<T>(string name) where T:class {return ui.FindName(name) as T;}
  string Folder {get{return Path.GetFullPath(Find<TextBox>("InstallPath").Text.Trim());}}
  string GameExe {get{return installed==null ? null : Path.Combine(installed,"mcla.exe");}}
  static bool Newer(string a,string b) {try{return new Version(a).CompareTo(new Version(b))>0;}catch{return false;}}
  string InstalledRelease() {try{var m=json.Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(installed,".mcla-br-install.json")));return m.ContainsKey("release")?Convert.ToString(m["release"]):"1.0.0";}catch{return "1.0.0";}}
  bool UpdateAvailable {get{return HasBundle&&installed!=null&&Newer(EmbeddedPayload.Version,InstalledRelease());}}
  public LauncherController(Window window) {
   ui=window;ui.Icon=ImageResource("setup.ico");Find<Image>("SideLogo").Source=ImageResource("logo.png");Find<Image>("HeroArt").Source=ImageResource("banner.png");
   string[] nav={"Home","Graphics","Profile","Saves","Logs","Credits"};
   foreach(string page in nav) {string id=page;Find<RadioButton>("Nav"+id).Checked+=delegate{Navigate(id);};}
   BuildGraphics();Find<ComboBox>("ButtonPrompts").SelectedIndex=0;firstRun=Selected();
   Find<TextBox>("InstallPath").Text=Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"MCLA_LA_Recompiled");
   try {if(File.Exists(preferences)) {var saved=json.Deserialize<Dictionary<string,string>>(File.ReadAllText(preferences));if(saved.ContainsKey("installation") && Owned(saved["installation"])) Find<TextBox>("InstallPath").Text=saved["installation"];}} catch(Exception e) {Log("Preferências: "+e.Message);}
   if(Owned(AppDomain.CurrentDomain.BaseDirectory)) Find<TextBox>("InstallPath").Text=Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);
   if(!HasBundle) {
    Find<FrameworkElement>("IsoLabel").Visibility=Find<FrameworkElement>("IsoRow").Visibility=Visibility.Collapsed;
    Find<Button>("PrepareButton").Visibility=Find<CheckBox>("DesktopShortcut").Visibility=Find<FrameworkElement>("TranslateCard").Visibility=Visibility.Collapsed;
    Find<TextBlock>("HomeInfo").Text="Use as abas para ajustar os gráficos, os controles e fazer backup dos seus dados. O atalho da Área de Trabalho abre o jogo diretamente.";
   }
   Find<TextBox>("InstallPath").LostKeyboardFocus+=delegate{Refresh(true);};
   Click("BrowseIso",delegate {var picker=new OpenFileDialog {Title="Sua ISO de Midnight Club: Los Angeles Complete Edition",Filter="Imagem de disco (*.iso)|*.iso",CheckFileExists=true};if(picker.ShowDialog(ui)==true) Find<TextBox>("IsoPath").Text=picker.FileName;});
   Click("BrowseInstall",delegate{ChooseFolder(!HasBundle);});Click("LocateButton",delegate{ChooseFolder(true);});
   Click("PlayButton",Play);Click("OpenGameFolder",delegate{OpenDirectory(installed??Folder);});
   Find<Button>("PrepareButton").Click+=async delegate {await Prepare();};
   Click("PresetLight",delegate{Preset("Leve");});Click("PresetBalanced",delegate{Preset("Equilibrado");});Click("PresetNative",delegate{Preset("Native AA");});
   Click("ApplyGraphics",Apply);Click("ApplyProfile",Apply);
   Click("OpenSaves",delegate{OpenDirectory(SaveDirectory());});Click("BackupSaves",Backup);
   Click("CopyLogs",delegate{Clipboard.SetText(Find<TextBox>("LogText").Text);Status("Registro copiado.");});
   Click("OpenLogs",delegate{if(installed!=null) OpenDirectory(Path.Combine(installed,"logs"));});
   Click("OpenLicenses",delegate{if(installed!=null) OpenDirectory(Path.Combine(installed,"licenses"));else Status("Os créditos e as licenças acompanham a instalação do jogo.");});
   ui.Closing+=delegate(object sender,System.ComponentModel.CancelEventArgs e) {if(working){e.Cancel=true;Status("A preparação está em andamento. Aguarde o término para fechar.");}};
   Refresh(true);Log("Configurador pronto. Use sua própria ISO ou localize uma instalação preparada por este programa.");
  }
  BitmapSource ImageResource(string name) {using(var s=Assembly.GetExecutingAssembly().GetManifestResourceStream("MclaSetup."+name)) {var b=new BitmapImage();b.BeginInit();b.CacheOption=BitmapCacheOption.OnLoad;b.StreamSource=s;b.EndInit();b.Freeze();return b;}}
  void Click(string id,Action action) {Find<Button>(id).Click+=delegate{try{action();}catch(Exception e){Error(e);}};}
  void Navigate(string id) {foreach(string p in new[]{"Home","Graphics","Profile","Saves","Logs","Credits"}) Find<FrameworkElement>("Page"+p).Visibility=p==id?Visibility.Visible:Visibility.Collapsed;if(id=="Saves") RefreshSaves();}
  void Go(string id) {Find<RadioButton>("Nav"+id).IsChecked=true;Navigate(id);}
  void Status(string text) {Find<TextBlock>("StatusText").Text=text;}
  void Log(string text) {if(String.IsNullOrEmpty(text))return;if(!ui.Dispatcher.CheckAccess()){ui.Dispatcher.BeginInvoke(new Action<string>(Log),text);return;}Find<TextBox>("LogText").AppendText(text+Environment.NewLine);Find<TextBox>("LogText").ScrollToEnd();if(text.StartsWith("[ETAPA")) Status(text);}
  void Error(Exception error) {Log("ERRO: "+error.Message);Status(error.Message);MessageBox.Show(ui,error.Message,"Midnight Club L.A. Recompiled",MessageBoxButton.OK,MessageBoxImage.Information);}
  bool Owned(string folder) {try {var marker=Path.Combine(folder,".mcla-br-install.json");if(!File.Exists(marker)||!File.Exists(Path.Combine(folder,"mcla.exe")))return false;var m=json.Deserialize<Dictionary<string,object>>(File.ReadAllText(marker));return Convert.ToString(m["identity"])=="mcla-la-recompiled" && Convert.ToString(m["phase"])=="ready";}catch{return false;}}
  void ChooseFolder(bool mustExist) {using(var picker=new System.Windows.Forms.FolderBrowserDialog {ShowNewFolderButton=!mustExist,Description=mustExist?"Escolha a pasta que contém mcla.exe e a instalação preparada":"Escolha uma subpasta para o jogo"}) {if(picker.ShowDialog()!=System.Windows.Forms.DialogResult.OK)return;if(mustExist&&!Owned(picker.SelectedPath))throw new IOException("Essa pasta não é uma instalação pronta deste configurador. Selecione a pasta que contém mcla.exe.");Find<TextBox>("InstallPath").Text=picker.SelectedPath;Refresh(true);}}
  void Refresh(bool read) {
   string folder;try{folder=Folder;}catch{folder="";}
   string previous=installed;installed=Owned(folder)?folder:null;
   if(installed==null && previous!=null) {loading=true;foreach(var pair in firstRun)Set(pair.Key,pair.Value);Set("window_size",firstRun["window_width"]+","+firstRun["window_height"]);Find<TextBox>("PlayerName").Text="User";Find<ComboBox>("ButtonPrompts").SelectedIndex=0;loading=false;Find<TextBlock>("PresetLabel").Text="Perfil: Padrão do jogo";}
   Find<TextBlock>("InstallStatus").Text=installed==null?"Prepare seu jogo":"Tudo pronto";
   Find<TextBlock>("HomeActionHint").Text=installed==null?"Sua ISO será necessária apenas na preparação.":"Configurações e saves desta instalação reconhecidos.";
   ShowMode();
   Find<Button>("PlayButton").IsEnabled=installed!=null&&!working;
   Find<Button>("ApplyGraphics").Content=installed==null?"USAR ESTAS OPÇÕES NA PREPARAÇÃO":"SALVAR CONFIGURAÇÕES";
   Find<Button>("ApplyProfile").Content=installed==null?"USAR ESTE PERFIL NA PREPARAÇÃO":"SALVAR PERFIL E CONTROLES";
   if(installed!=null) {if(read)LoadSettings();SavePreferences();Status("Instalação reconhecida. Você já pode jogar.");}
   RefreshSaves();
  }
  void ShowMode() {
   if(!HasBundle)return;
   bool update=UpdateAvailable;
   Find<TextBlock>("InstallStatus").Text=update?"Atualização disponível":installed==null?"Prepare seu jogo":"Tudo pronto";
   Find<TextBlock>("HomeActionHint").Text=update?"v"+InstalledRelease()+" → v"+EmbeddedPayload.Version+". Seus saves e configurações serão mantidos; a ISO não é necessária.":installed==null?"Sua ISO será necessária apenas na preparação.":"Configurações e saves desta instalação reconhecidos.";
   Find<Button>("PrepareButton").Content=update?"ATUALIZAR PARA A v"+EmbeddedPayload.Version:installed!=null?"REINSTALAR COM A ISO":"PREPARAR MEU JOGO";
   var show=update?Visibility.Collapsed:Visibility.Visible;
   Find<FrameworkElement>("IsoLabel").Visibility=Find<FrameworkElement>("IsoRow").Visibility=Find<FrameworkElement>("TranslateCard").Visibility=Find<CheckBox>("DesktopShortcut").Visibility=show;
   if(installed!=null&&!update)Find<CheckBox>("TranslateGame").IsChecked=File.Exists(Path.Combine(installed,"game",".mcla-ptbr.json"));
   Find<TextBlock>("HomeInfo").Text=update?"Esta atualização troca os arquivos do jogo e acrescenta as traduções novas sobre as que você já tem. Seus saves e o mcla.toml não são alterados; uma cópia dos saves e dos arquivos anteriores fica na pasta backups.":"Use sua própria ISO de Midnight Club: Los Angeles Complete Edition para Xbox 360.";
  }
  void SavePreferences() {if(installed==null)return;Directory.CreateDirectory(Path.GetDirectoryName(preferences));File.WriteAllText(preferences,json.Serialize(new Dictionary<string,string>{{"installation",installed}}),Encoding.UTF8);}
  StackPanel Group(string title) {var border=new Border {Style=(Style)ui.Resources["Card"],Margin=new Thickness(0,0,0,18)};var stack=new StackPanel();stack.Children.Add(new TextBlock {Text=title,FontWeight=FontWeights.Bold,Foreground=(Brush)ui.Resources["Accent"],Margin=new Thickness(0,0,0,16)});border.Child=stack;Find<StackPanel>("GraphicsGroups").Children.Add(border);return stack;}
  void Choice(StackPanel parent,string label,string key,string[] labels,string[] values,int selected) {var row=new Grid {Margin=new Thickness(0,0,0,13)};row.ColumnDefinitions.Add(new ColumnDefinition {Width=new GridLength(1,GridUnitType.Star)});row.ColumnDefinitions.Add(new ColumnDefinition {Width=new GridLength(1.15,GridUnitType.Star)});row.Children.Add(new TextBlock {Text=label,VerticalAlignment=VerticalAlignment.Center,TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,0,16,0)});var c=new ComboBox {MinWidth=200};for(int i=0;i<labels.Length;i++)c.Items.Add(new ComboBoxItem {Content=labels[i],Tag=values[i]});c.SelectedIndex=selected;System.Windows.Automation.AutomationProperties.SetName(c,label);Grid.SetColumn(c,1);row.Children.Add(c);parent.Children.Add(row);choices[key]=c;c.SelectionChanged+=delegate{if(!loading)Find<TextBlock>("PresetLabel").Text="Perfil: Personalizado";};}
  void Toggle(StackPanel parent,string label,string key,bool initial) {var check=new CheckBox {Content=label,IsChecked=initial,Margin=new Thickness(0,0,0,17)};parent.Children.Add(check);toggles[key]=check;check.Checked+=delegate{if(!loading)Find<TextBlock>("PresetLabel").Text="Perfil: Personalizado";};check.Unchecked+=delegate{if(!loading)Find<TextBlock>("PresetLabel").Text="Perfil: Personalizado";};}
  void BuildGraphics() {
   loading=true;var g=Group("TELA E APRESENTAÇÃO");
   Choice(g,"Modo de exibição","fullscreen",new[]{"Tela cheia (resolução do monitor)","Janela"},new[]{"true","false"},0);
   Choice(g,"Tamanho da janela","window_size",new[]{"Automático","1280 × 720","1920 × 1080","2560 × 1440","3440 × 1440","3840 × 2160"},new[]{"0,0","1280,720","1920,1080","2560,1440","3440,1440","3840,2160"},0);
   Choice(g,"Proporção","mcla_aspect_ratio",new[]{"Automático","16:9","21:9"},new[]{"auto","16:9","43:18"},0);
   Choice(g,"Resolução de renderização","resolution_scale",new[]{"720p (1×)","1440p (2×)","2160p (3×)"},new[]{"1","2","3"},0);
   Choice(g,"API gráfica","mcla_gpu_backend",new[]{"Automático","DirectX 12","Vulkan"},new[]{"any","d3d12","vulkan"},0);
   Choice(g,"Sincronização vertical","vsync",new[]{"Não","Sim"},new[]{"false","true"},1);
   Choice(g,"Limite de FPS","mcla_fps",new[]{"Sem limite","30","60","90","120","144"},new[]{"0","30","60","90","120","144"},1);
   Choice(g,"HDR","hdr",new[]{"Desligado","Automático","Ligado"},new[]{"off","auto","on"},0);
   Choice(g,"Gama de exibição","mcla_display_gamma",new[]{"Monitor de PC","TV"},new[]{"pc","tv"},1);
   g=Group("AMD FIDELITYFX");Choice(g,"Antisserrilhado","mcla_anti_aliasing",new[]{"FSR 4.1.2","MSAA 2×","Desligado"},new[]{"fsr","msaa","off"},1);
   Choice(g,"Modo FSR","temporal_aa_quality",new[]{"Native AA","Qualidade","Equilibrado","Desempenho"},new[]{"native","quality","balanced","performance"},0);
   Choice(g,"Nitidez FSR","temporal_aa_sharpness",new[]{"Desligada","0,2","0,4","0,6","0,8","1,0"},new[]{"0","0.2","0.4","0.6","0.8","1.0"},1);
   Toggle(g,"FRAME GENERATION 4.0.2","frame_generation",false);g.Children.Add(new TextBlock {Text="FSR 4.1.2 e Frame Generation por IA só funcionam no DirectX 12 com hardware compatível; em Vulkan o FSR é o 3.1 e a Frame Generation não gera quadros (deixe desligada). Em tela cheia, a saída acompanha a resolução do monitor.",Style=(Style)ui.Resources["Hint"],FontSize=11});
   g=Group("SOMBRAS E EFEITOS");foreach(var p in new[]{new[]{"Sombras","mcla_shadows"},new[]{"Sombras nas corridas","mcla_race_shadows"},new[]{"Sombras da vegetação","mcla_foliage_shadows"},new[]{"Árvores distantes","mcla_foliage_impostors"}})Toggle(g,p[0],p[1],true);
   foreach(var p in new[]{new[]{"Sombras simples dos carros","mcla_fast_car_shadows"},new[]{"Desfoque de movimento","mcla_motion_blur"},new[]{"Profundidade de campo","mcla_depth_of_field"},new[]{"Desfoque de tela","mcla_fullscreen_blur"}})Toggle(g,p[0],p[1],p[1]!="mcla_fast_car_shadows");
   g=Group("CIDADE E TRÁFEGO");foreach(var p in new[]{new[]{"Detalhe da cidade","mcla_city_lod"},new[]{"Detalhe do tráfego","mcla_traffic_lod"},new[]{"Pedestres","mcla_pedestrians"},new[]{"Carros estacionados","mcla_parked_cars"}})Choice(g,p[0],p[1],new[]{"100%","75%","50%","25%"},new[]{"1.0","0.75","0.5","0.25"},0);
   choices["mcla_gpu_backend"].SelectionChanged+=delegate{bool dx=Value("mcla_gpu_backend")=="d3d12";toggles["frame_generation"].IsEnabled=dx;if(!dx)toggles["frame_generation"].IsChecked=false;};
   choices["mcla_anti_aliasing"].SelectionChanged+=delegate{bool fsr=Value("mcla_anti_aliasing")=="fsr";choices["temporal_aa_quality"].IsEnabled=choices["temporal_aa_sharpness"].IsEnabled=fsr;};toggles["frame_generation"].IsEnabled=false;choices["temporal_aa_quality"].IsEnabled=choices["temporal_aa_sharpness"].IsEnabled=false;loading=false;
  }
  string Value(string key) {var item=choices[key].SelectedItem as ComboBoxItem;return item==null?"":Convert.ToString(item.Tag);}
  void Set(string key,string value) {if(choices.ContainsKey(key))foreach(ComboBoxItem item in choices[key].Items)if(Convert.ToString(item.Tag)==value){choices[key].SelectedItem=item;return;}if(toggles.ContainsKey(key))toggles[key].IsChecked=key=="frame_generation"?value=="fsr":value=="true";}
  void Preset(string name) {loading=true;bool light=name=="Leve";Set("resolution_scale",light?"1":"2");Set("mcla_anti_aliasing","fsr");Set("temporal_aa_quality",light?"performance":name=="Native AA"?"native":"quality");Set("temporal_aa_sharpness","0.2");foreach(string k in new[]{"mcla_shadows","mcla_race_shadows","mcla_foliage_shadows"})Set(k,light?"false":"true");Set("mcla_fast_car_shadows",light?"true":"false");foreach(string k in new[]{"mcla_city_lod","mcla_traffic_lod","mcla_pedestrians","mcla_parked_cars"})Set(k,light?"0.5":"1.0");foreach(string k in new[]{"mcla_motion_blur","mcla_depth_of_field","mcla_fullscreen_blur"})Set(k,"false");loading=false;Find<TextBlock>("PresetLabel").Text="Perfil: "+name;Status("Perfil selecionado. Salve as configurações ou prepare o jogo para aplicar.");}
  bool StringKey(string key) {return new[]{"mcla_gpu_backend","mcla_aspect_ratio","mcla_anti_aliasing","temporal_aa_quality","frame_generation","hdr","mcla_display_gamma","mcla_player_name","mcla_button_prompts"}.Contains(key);}
  Dictionary<string,string> Selected() {
   string name=Find<TextBox>("PlayerName").Text.Trim();if(!Regex.IsMatch(name,@"^[A-Za-z0-9_ ]{1,15}$")) {Go("Profile");throw new IOException("Escolha um nome de até 15 letras sem acento, números, espaço ou sublinhado.");}
   var values=new Dictionary<string,string>();foreach(var pair in choices) {string v=Value(pair.Key);if(pair.Key=="window_size"){var size=v.Split(',');values["window_width"]=size[0];values["window_height"]=size[1];}else values[pair.Key]=v;}
   foreach(var pair in toggles)values[pair.Key]=pair.Key=="frame_generation"?(pair.Value.IsChecked==true?"fsr":"off"):(pair.Value.IsChecked==true?"true":"false");
   if(Value("mcla_gpu_backend")!="d3d12") values["frame_generation"]="off";
   values["mcla_player_name"]=name;values["mcla_button_prompts"]=Convert.ToString(((ComboBoxItem)Find<ComboBox>("ButtonPrompts").SelectedItem).Tag);return values;
  }
  string Toml(Dictionary<string,string> values) {var text=new StringBuilder();foreach(var p in values)text.AppendLine(p.Key+" = "+(StringKey(p.Key)?json.Serialize(p.Value):p.Value));return text.ToString();}
  Dictionary<string,string> ReadConfig() {var result=new Dictionary<string,string>();if(installed==null)return result;string path=Path.Combine(installed,"mcla.toml");if(!File.Exists(path))return result;foreach(string line in File.ReadAllLines(path)){var m=Regex.Match(line,@"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$");if(!m.Success)continue;string value=m.Groups[2].Value;try {if(value.StartsWith("\""))value=json.Deserialize<string>(value);else value=value.Split('#')[0].Trim();result[m.Groups[1].Value]=value;}catch{}}return result;}
  void LoadSettings() {loading=true;var values=ReadConfig();foreach(var pair in values)Set(pair.Key,pair.Value);if(values.ContainsKey("window_width")&&values.ContainsKey("window_height"))Set("window_size",values["window_width"]+","+values["window_height"]);if(values.ContainsKey("mcla_player_name"))Find<TextBox>("PlayerName").Text=values["mcla_player_name"];if(values.ContainsKey("mcla_button_prompts"))foreach(ComboBoxItem i in Find<ComboBox>("ButtonPrompts").Items)if(Convert.ToString(i.Tag)==values["mcla_button_prompts"])Find<ComboBox>("ButtonPrompts").SelectedItem=i;loading=false;Find<TextBlock>("PresetLabel").Text="Perfil: Configurações da instalação";}
  bool GameRunning() {if(installed==null)return false;foreach(var p in Process.GetProcessesByName("mcla")) {try{if(String.Equals(p.MainModule.FileName,GameExe,StringComparison.OrdinalIgnoreCase))return true;}catch{}finally{p.Dispose();}}return false;}
  void Apply() {var values=Selected();if(installed==null){Status("Opções selecionadas. Elas serão aplicadas ao preparar o jogo.");return;}if(GameRunning())throw new IOException("Feche o jogo antes de salvar as configurações no configurador.");string path=Path.Combine(installed,"mcla.toml");string old=File.Exists(path)?File.ReadAllText(path):"";foreach(string key in values.Keys)old=Regex.Replace(old,@"^\s*"+Regex.Escape(key)+@"\s*=.*(?:\r?\n|$)","",RegexOptions.Multiline);string fresh=path+".new";File.WriteAllText(fresh,old+Environment.NewLine+"# Configurações do launcher"+Environment.NewLine+Toml(values),new UTF8Encoding(false));if(File.Exists(path)){string backups=Path.Combine(installed,"config-backups");Directory.CreateDirectory(backups);File.Replace(fresh,path,Path.Combine(backups,DateTime.Now.ToString("yyyyMMdd-HHmmss-ffff")+".toml"));}else File.Move(fresh,path);Status("Configurações salvas. Valem na próxima abertura do jogo.");Log("Configurações salvas em "+path);}
  void Play() {if(installed==null||!Owned(installed))throw new IOException("Localize uma instalação pronta antes de jogar.");if(GameRunning()){Status("O jogo já está aberto.");return;}Process.Start(new ProcessStartInfo(GameExe) {WorkingDirectory=installed,UseShellExecute=true});Status("Jogo iniciado. Divirta-se!");}
  void OpenDirectory(string path) {if(path==null||!Directory.Exists(path))throw new IOException("Essa pasta ainda não existe. Inicie ou prepare o jogo primeiro.");Process.Start("explorer.exe",Quote(path));}
  string SaveDirectory() {if(installed==null)return null;var values=ReadConfig();string path=values.ContainsKey("user_data_root")?values["user_data_root"]:Path.Combine(installed,"userdata");return Path.IsPathRooted(path)?path:Path.Combine(installed,path);}
  void RefreshSaves() {try {string path=SaveDirectory();Find<TextBlock>("SavePath").Text=path??"Prepare ou localize uma instalação.";if(path!=null&&Directory.Exists(path)){var files=new DirectoryInfo(path).GetFiles("*",SearchOption.AllDirectories);Find<TextBlock>("SaveSummary").Text=files.Length+" arquivos · "+(files.Sum(f=>f.Length)/1048576.0).ToString("0.0",CultureInfo.CurrentCulture)+" MB";}else Find<TextBlock>("SaveSummary").Text="Os dados serão criados ao iniciar e salvar o jogo.";}catch(Exception e){Find<TextBlock>("SaveSummary").Text=e.Message;}}
  void Backup() {if(GameRunning())throw new IOException("Feche o jogo antes de exportar o backup.");string path=SaveDirectory();if(path==null||!Directory.Exists(path))throw new IOException("Ainda não há dados de usuário para exportar.");var picker=new SaveFileDialog {Title="Exportar backup dos dados",Filter="Arquivo ZIP (*.zip)|*.zip",FileName="MCLA-save-"+DateTime.Now.ToString("yyyyMMdd-HHmmss")+".zip",InitialDirectory=Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)};if(picker.ShowDialog(ui)!=true)return;string dest=Path.GetFullPath(picker.FileName);string prefix=Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;if(dest.StartsWith(prefix,StringComparison.OrdinalIgnoreCase))throw new IOException("Salve o backup fora da pasta dos dados.");ZipFile.CreateFromDirectory(path,dest,CompressionLevel.Optimal,false);Status("Backup exportado: "+dest);}
  static string Quote(string value) {return "\""+value.Replace("\"","")+"\"";}
  async Task Prepare() {
   string script=null;
   try {
    if(working)return;if(!HasBundle)throw new IOException("Use o instalador completo para preparar uma ISO.");bool update=UpdateAvailable;var selected=update?null:Selected();bool translate=Find<CheckBox>("TranslateGame").IsChecked==true;string target=Folder;string iso=update?"":Find<TextBox>("IsoPath").Text.Trim();if(!update&&(!File.Exists(iso)||!String.Equals(Path.GetExtension(iso),".iso",StringComparison.OrdinalIgnoreCase)))throw new IOException("Selecione uma ISO existente pelo botão Procurar ISO.");
    string self=Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar);if(String.Equals(target.TrimEnd(Path.DirectorySeparatorChar),self,StringComparison.OrdinalIgnoreCase))throw new IOException("Escolha uma subpasta para o jogo. O destino não pode ser a própria pasta do instalador.");if(GameRunning())throw new IOException("Feche o jogo antes de preparar ou atualizar essa instalação.");
    Go("Logs");Log(update?"Iniciando a atualização…":"Iniciando preparação do jogo…");working=true;Find<Button>("PrepareButton").IsEnabled=false;Find<Button>("PlayButton").IsEnabled=false;Find<StackPanel>("Navigation").IsEnabled=false;Find<TextBox>("InstallPath").IsEnabled=Find<TextBox>("IsoPath").IsEnabled=false;Find<Button>("BrowseInstall").IsEnabled=Find<Button>("BrowseIso").IsEnabled=false;Find<ProgressBar>("WorkProgress").IsIndeterminate=true;Status("Verificando e extraindo o pacote interno…");
    string bundle=await Task.Run(delegate{return EmbeddedPayload.Extract(null);});string scratch=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"MCLA_LA_Recompiled","Setup");Directory.CreateDirectory(scratch);script=Path.Combine(scratch,"bootstrap-"+Guid.NewGuid().ToString("N")+".ps1");using(var input=Assembly.GetExecutingAssembly().GetManifestResourceStream("MclaSetup.bootstrap.ps1"))using(var output=File.Create(script))input.CopyTo(output);
    string common=" -InstallDirectory "+Quote(target)+" -InstallerDirectory "+Quote(self)+" -BundleDirectory "+Quote(bundle);string mode;if(update)mode=" -Update";else mode=" -Iso "+Quote(Path.GetFullPath(iso))+" -GraphicsSettings "+Quote(Convert.ToBase64String(Encoding.UTF8.GetBytes(Toml(selected))))+" -Translate "+(translate?"1":"0");var start=new ProcessStartInfo("powershell.exe","-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "+Quote(script)+common+mode) {UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true,StandardOutputEncoding=Encoding.UTF8,StandardErrorEncoding=Encoding.UTF8};worker=new Process {StartInfo=start};worker.OutputDataReceived+=delegate(object sender,DataReceivedEventArgs e){Log(e.Data);};worker.ErrorDataReceived+=delegate(object sender,DataReceivedEventArgs e){Log(e.Data);};worker.Start();worker.BeginOutputReadLine();worker.BeginErrorReadLine();await Task.Run(delegate{worker.WaitForExit();});if(worker.ExitCode!=0||!Owned(target))throw new IOException("A preparação não terminou. Veja as mensagens na aba Registro.");string launcherTarget=Path.Combine(target,"Midnight Club L.A. Recompiled.exe");string launcherSource=Assembly.GetExecutingAssembly().Location;if(!String.Equals(Path.GetFullPath(launcherSource),Path.GetFullPath(launcherTarget),StringComparison.OrdinalIgnoreCase)){File.Copy(launcherSource,launcherTarget,true);Log("Instalador e configurador disponíveis no mesmo executável: "+launcherTarget);}installed=target;SavePreferences();if(Find<CheckBox>("DesktopShortcut").IsChecked==true){try{GameShortcut.Create(target);Log("Atalho direto criado na Área de Trabalho.");}catch(Exception e){Log("Jogo pronto; não foi possível criar o atalho: "+e.Message);}}Refresh(true);Status(update?"Atualizado. Seus saves e configurações foram mantidos.":"Tudo pronto. Seu jogo já pode ser iniciado.");
   }catch(Exception e){Error(e);Go("Logs");}
   finally {working=false;Find<Button>("PrepareButton").IsEnabled=true;Find<StackPanel>("Navigation").IsEnabled=true;Find<TextBox>("InstallPath").IsEnabled=Find<TextBox>("IsoPath").IsEnabled=true;Find<Button>("BrowseInstall").IsEnabled=Find<Button>("BrowseIso").IsEnabled=true;Find<ProgressBar>("WorkProgress").IsIndeterminate=false;Find<ProgressBar>("WorkProgress").Value=installed!=null?100:0;Find<Button>("PlayButton").IsEnabled=installed!=null;if(worker!=null){worker.Dispose();worker=null;}if(script!=null&&File.Exists(script))File.Delete(script);try{string directory=Path.GetDirectoryName(preferences);Directory.CreateDirectory(directory);File.WriteAllText(Path.Combine(directory,"last-install.log"),Find<TextBox>("LogText").Text);}catch{}}
  }
 }
}
