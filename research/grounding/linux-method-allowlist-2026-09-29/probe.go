package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"time"
)

const (
	probePath   = "/probe/probe"
	backendPath = "/probe/backend"
	otherPath   = "/probe/undeclared"
	scratchPath = "/work/scratch"
	workPath    = "/work"
	maxRun      = 10 * time.Second
	ioBound     = time.Second
)

type childReport struct {
	Operation       string `json:"operation"`
	PID             int    `json:"pid"`
	PPID            int    `json:"ppid"`
	UID             int    `json:"uid"`
	EUID            int    `json:"euid"`
	Executable      string `json:"executable"`
	Argv0           string `json:"argv0"`
	ExecTag         string `json:"exec_tag,omitempty"`
	Target          string `json:"target,omitempty"`
	Network         string `json:"network,omitempty"`
	Address         string `json:"address,omitempty"`
	Payload         string `json:"payload,omitempty"`
	Attempted       bool   `json:"attempted"`
	ActionSucceeded bool   `json:"action_succeeded"`
	ActionError     string `json:"action_error,omitempty"`
	GoVersion       string `json:"go_version"`
	GOOS            string `json:"goos"`
	GOARCH          string `json:"goarch"`
}

type fileIdentity struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256,omitempty"`
	Error  string `json:"error,omitempty"`
}

type processResult struct {
	Argv            []string     `json:"argv"`
	PID             *int         `json:"pid"`
	ReturnCode      *int         `json:"return_code"`
	StartError      string       `json:"start_error,omitempty"`
	WaitError       string       `json:"wait_error,omitempty"`
	TimedOut        bool         `json:"timed_out"`
	ElapsedMS       int64        `json:"elapsed_ms"`
	Stdout          string       `json:"stdout"`
	Stderr          string       `json:"stderr"`
	StdoutTruncated bool         `json:"stdout_truncated"`
	StderrTruncated bool         `json:"stderr_truncated"`
	ChildReport     *childReport `json:"child_report,omitempty"`
}

type observation struct {
	Mode                 string       `json:"mode"`
	Argv                 []string     `json:"argv"`
	PID                  *int         `json:"pid"`
	ReturnCode           *int         `json:"return_code"`
	SetupError           string       `json:"setup_error,omitempty"`
	StartError           string       `json:"start_error,omitempty"`
	WaitError            string       `json:"wait_error,omitempty"`
	TimedOut             bool         `json:"timed_out"`
	ElapsedMS            int64        `json:"elapsed_ms"`
	Stdout               string       `json:"stdout"`
	Stderr               string       `json:"stderr"`
	StdoutTruncated      bool         `json:"stdout_truncated"`
	StderrTruncated      bool         `json:"stderr_truncated"`
	ChildStarted         bool         `json:"child_started"`
	ChildParseError      string       `json:"child_parse_error,omitempty"`
	ChildReport          *childReport `json:"child_report,omitempty"`
	ActionSucceeded      *bool        `json:"action_succeeded"`
	ActionError          string       `json:"action_error,omitempty"`
	FilePath             string       `json:"file_path,omitempty"`
	FileCreated          *bool        `json:"file_created"`
	FileContent          string       `json:"file_content,omitempty"`
	FileContentMatches   *bool        `json:"file_content_matches"`
	ListenerAddress      string       `json:"listener_address,omitempty"`
	PayloadReceived      *bool        `json:"payload_received"`
	ExactPayloadReceived *bool        `json:"exact_payload_received"`
	ReceivedPayload      string       `json:"received_payload,omitempty"`
	ReceiptError         string       `json:"receipt_error,omitempty"`
}

type caseResult struct {
	ID          string       `json:"id"`
	Description string       `json:"description"`
	SetupError  string       `json:"setup_error,omitempty"`
	Control     *observation `json:"control,omitempty"`
	BestEffort  *observation `json:"best_effort,omitempty"`
	Strict      *observation `json:"strict,omitempty"`
}

type expectationResult struct {
	Expression string `json:"expression"`
	Expected   bool   `json:"expected"`
	Actual     *bool  `json:"actual"`
	Passed     bool   `json:"passed"`
}

type metadata struct {
	PID                int                     `json:"pid"`
	UID                int                     `json:"uid"`
	EUID               int                     `json:"euid"`
	GoVersion          string                  `json:"go_version"`
	GOOS               string                  `json:"goos"`
	GOARCH             string                  `json:"goarch"`
	WorkingDirectory   string                  `json:"working_directory"`
	KernelRelease      string                  `json:"kernel_release"`
	KernelReleaseError string                  `json:"kernel_release_error,omitempty"`
	KernelVersion      string                  `json:"kernel_version"`
	KernelVersionError string                  `json:"kernel_version_error,omitempty"`
	Binaries           map[string]fileIdentity `json:"binaries"`
	Landrun            fileIdentity            `json:"landrun"`
	LandrunVersion     processResult           `json:"landrun_version"`
}

type limitation struct {
	ID     string `json:"id"`
	Status string `json:"status"`
	Reason string `json:"reason"`
}

type report struct {
	SchemaVersion   int                 `json:"schema_version"`
	Tool            string              `json:"tool"`
	MeasurementOnly bool                `json:"measurement_only"`
	NoClaim         string              `json:"no_claim"`
	Metadata        metadata            `json:"metadata"`
	SetupErrors     []string            `json:"setup_errors"`
	Cases           []caseResult        `json:"cases"`
	Limitations     []limitation        `json:"limitations"`
	Expectations    []expectationResult `json:"expectations"`
}

type networkControl struct {
	kind    string
	address string
	close   func() error
	read    func() ([]byte, error)
}

type limitedBuffer struct {
	buffer    bytes.Buffer
	limit     int
	truncated bool
}

func (b *limitedBuffer) Write(value []byte) (int, error) {
	length := len(value)
	remaining := b.limit - b.buffer.Len()
	if remaining > length {
		remaining = length
	}
	if remaining > 0 {
		_, _ = b.buffer.Write(value[:remaining])
	}
	if remaining < length {
		b.truncated = true
	}
	return length, nil
}

func (b *limitedBuffer) String() string {
	return b.buffer.String()
}

func main() {
	if len(os.Args) >= 2 && os.Args[1] == "child" {
		if err := runChild(os.Args[2:]); err != nil {
			writeJSON(childReport{Operation: "invalid_invocation", PID: os.Getpid(), PPID: os.Getppid(), ActionError: err.Error()})
			os.Exit(2)
		}
		return
	}
	if len(os.Args) < 2 || os.Args[1] != "harness" {
		writeJSON(map[string]any{"error": "usage: probe harness [--landrun PATH] [--expect CASE:RUN:FIELD=VALUE]"})
		os.Exit(2)
	}
	landrun, expects, err := parseHarnessArgs(os.Args[2:])
	if err != nil {
		writeJSON(map[string]any{"error": err.Error()})
		os.Exit(2)
	}
	doc, code := runHarness(landrun, expects)
	writeJSON(doc)
	os.Exit(code)
}

func runChild(args []string) error {
	if len(args) == 0 {
		return errors.New("missing child operation")
	}
	switch args[0] {
	case "identify":
		if len(args) != 1 {
			return errors.New("identify takes no arguments")
		}
		executable, err := os.Executable()
		if err != nil {
			executable = ""
		}
		writeJSON(childReport{
			Operation:  "identify",
			PID:        os.Getpid(),
			PPID:       os.Getppid(),
			UID:        os.Getuid(),
			EUID:       os.Geteuid(),
			Executable: executable,
			Argv0:      os.Args[0],
			ExecTag:    os.Getenv("CAIRN_PROBE_EXEC_TAG"),
			GoVersion:  runtime.Version(),
			GOOS:       runtime.GOOS,
			GOARCH:     runtime.GOARCH,
		})
		return nil
	case "exec":
		if len(args) != 3 {
			return errors.New("exec requires a tag and target path")
		}
		return execTarget(args[1], args[2])
	case "write":
		if len(args) != 3 {
			return errors.New("write requires a path and payload")
		}
		return writeTarget(args[1], args[2])
	case "network":
		if len(args) != 4 {
			return errors.New("network requires a network, address, and payload")
		}
		return writeNetwork(args[1], args[2], args[3])
	case "fd-write":
		if len(args) != 2 {
			return errors.New("fd-write requires a payload")
		}
		return writeFD(args[1])
	case "fd-network":
		if len(args) != 2 {
			return errors.New("fd-network requires a payload")
		}
		return writeNetworkFD(args[1])
	case "fd-exec":
		if len(args) != 2 {
			return errors.New("fd-exec requires an exec tag")
		}
		return execTarget(args[1], "/proc/self/fd/3")
	default:
		return fmt.Errorf("unknown child operation %q", args[0])
	}
}

func execTarget(tag, target string) error {
	env := append([]string{}, os.Environ()...)
	env = append(env, "CAIRN_PROBE_EXEC_TAG="+tag)
	err := syscall.Exec(target, []string{target, "child", "identify"}, env)
	writeJSON(childReport{
		Operation:       "exec",
		PID:             os.Getpid(),
		PPID:            os.Getppid(),
		UID:             os.Getuid(),
		EUID:            os.Geteuid(),
		Executable:      executablePath(),
		Argv0:           os.Args[0],
		ExecTag:         tag,
		Target:          target,
		Attempted:       true,
		ActionSucceeded: false,
		ActionError:     err.Error(),
		GoVersion:       runtime.Version(),
		GOOS:            runtime.GOOS,
		GOARCH:          runtime.GOARCH,
	})
	return nil
}

func writeTarget(path, payload string) error {
	f, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		writeAction("write", path, "", payload, false, err)
		return nil
	}
	defer f.Close()
	n, writeErr := io.WriteString(f, payload)
	if writeErr == nil && n != len(payload) {
		writeErr = io.ErrShortWrite
	}
	writeAction("write", path, "", payload, writeErr == nil, writeErr)
	return nil
}

func writeNetwork(network, address, payload string) error {
	conn, err := net.DialTimeout(network, address, ioBound)
	if err != nil {
		writeNetworkAction(network, address, payload, false, err)
		return nil
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(ioBound))
	n, writeErr := io.WriteString(conn, payload)
	if writeErr == nil && n != len(payload) {
		writeErr = io.ErrShortWrite
	}
	writeNetworkAction(network, address, payload, writeErr == nil, writeErr)
	return nil
}

func writeFD(payload string) error {
	f := os.NewFile(uintptr(3), "inherited-writable-fd")
	if f == nil {
		writeAction("fd-write", "fd:3", "", payload, false, errors.New("file descriptor 3 is unavailable"))
		return nil
	}
	defer f.Close()
	n, err := io.WriteString(f, payload)
	if err == nil && n != len(payload) {
		err = io.ErrShortWrite
	}
	writeAction("fd-write", "fd:3", "", payload, err == nil, err)
	return nil
}

func writeNetworkFD(payload string) error {
	f := os.NewFile(uintptr(3), "inherited-connected-socket")
	if f == nil {
		writeNetworkAction("inherited-tcp4", "fd:3", payload, false, errors.New("file descriptor 3 is unavailable"))
		return nil
	}
	defer f.Close()
	conn, err := net.FileConn(f)
	if err != nil {
		writeNetworkAction("inherited-tcp4", "fd:3", payload, false, err)
		return nil
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(ioBound))
	n, writeErr := io.WriteString(conn, payload)
	if writeErr == nil && n != len(payload) {
		writeErr = io.ErrShortWrite
	}
	writeNetworkAction("inherited-tcp4", "fd:3", payload, writeErr == nil, writeErr)
	return nil
}

func writeAction(operation, target, network, payload string, succeeded bool, err error) {
	r := childReport{
		Operation:       operation,
		PID:             os.Getpid(),
		PPID:            os.Getppid(),
		UID:             os.Getuid(),
		EUID:            os.Geteuid(),
		Executable:      executablePath(),
		Argv0:           os.Args[0],
		Target:          target,
		Network:         network,
		Payload:         payload,
		Attempted:       true,
		ActionSucceeded: succeeded,
		GoVersion:       runtime.Version(),
		GOOS:            runtime.GOOS,
		GOARCH:          runtime.GOARCH,
	}
	if err != nil {
		r.ActionError = err.Error()
	}
	writeJSON(r)
}

func writeNetworkAction(network, address, payload string, succeeded bool, err error) {
	r := childReport{
		Operation:       "network",
		PID:             os.Getpid(),
		PPID:            os.Getppid(),
		UID:             os.Getuid(),
		EUID:            os.Geteuid(),
		Executable:      executablePath(),
		Argv0:           os.Args[0],
		Network:         network,
		Address:         address,
		Payload:         payload,
		Attempted:       true,
		ActionSucceeded: succeeded,
		ActionError:     errorString(err),
		GoVersion:       runtime.Version(),
		GOOS:            runtime.GOOS,
		GOARCH:          runtime.GOARCH,
	}
	writeJSON(r)
}

func parseHarnessArgs(args []string) (string, []string, error) {
	landrun := "/usr/local/bin/landrun"
	var expects []string
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--landrun":
			i++
			if i == len(args) || args[i] == "" {
				return "", nil, errors.New("--landrun requires a path")
			}
			landrun = args[i]
		case "--expect":
			i++
			if i == len(args) {
				return "", nil, errors.New("--expect requires an expression")
			}
			expects = append(expects, args[i])
		default:
			return "", nil, fmt.Errorf("unknown harness argument %q", args[i])
		}
	}
	return landrun, expects, nil
}

func runHarness(landrun string, expects []string) (report, int) {
	doc := report{
		SchemaVersion:   1,
		Tool:            "cairn-linux-method-probe",
		MeasurementOnly: true,
		NoClaim:         "Standalone candidate observations do not establish production method enforcement or a PROVEN claim.",
		Cases:           []caseResult{},
		SetupErrors:     []string{},
		Limitations: []limitation{
			{ID: "process-fork-without-exec", Status: "unimplemented", Reason: "A safe Linux arm64 fork path requires a raw child trampoline that makes no Go runtime calls; this probe does not provide one."},
			{ID: "dns", Status: "unmeasured", Reason: "No controlled local DNS responder is configured; no external DNS request is sent."},
			{ID: "inherited-descriptors", Status: "bounded-premise", Reason: "ExtraFiles deliberately supplies descriptors to this probe and does not show whether the production runner passes descriptors."},
		},
	}
	if err := os.MkdirAll(scratchPath, 0700); err != nil {
		doc.SetupErrors = append(doc.SetupErrors, "create scratch directory: "+err.Error())
	}
	if err := os.MkdirAll(workPath, 0700); err != nil {
		doc.SetupErrors = append(doc.SetupErrors, "create work directory: "+err.Error())
	}
	doc.Metadata = collectMetadata(landrun)
	if runtime.GOOS != "linux" || runtime.GOARCH != "arm64" {
		doc.SetupErrors = append(doc.SetupErrors, fmt.Sprintf("harness target is %s/%s, expected linux/arm64", runtime.GOOS, runtime.GOARCH))
	}
	if _, err := os.Stat(probePath); err != nil {
		doc.SetupErrors = append(doc.SetupErrors, "counted probe binary: "+err.Error())
	}
	if _, err := os.Stat(backendPath); err != nil {
		doc.SetupErrors = append(doc.SetupErrors, "declared backend binary: "+err.Error())
	}
	if _, err := os.Stat(otherPath); err != nil {
		doc.SetupErrors = append(doc.SetupErrors, "undeclared binary: "+err.Error())
	}
	if len(doc.SetupErrors) > 0 {
		return doc, 2
	}

	runIdentityCase(&doc, landrun)
	runExecCase(&doc, landrun, "exec-declared-backend", "Declared backend exec", backendPath, false)
	runExecCase(&doc, landrun, "exec-undeclared", "Undeclared binary exec", otherPath, false)
	runExecCase(&doc, landrun, "exec-self-reexec", "Counted binary self reexec", probePath, false)
	runSymlinkExecCase(&doc, landrun, "exec-symlink-allowed", "Symlink exec to declared backend", backendPath)
	runSymlinkExecCase(&doc, landrun, "exec-symlink-undeclared", "Symlink exec to undeclared binary", otherPath)
	runWriteCase(&doc, landrun, "write-scratch", "Scratch write", true)
	runWriteCase(&doc, landrun, "write-outside", "Outside-scratch write", false)
	runPreopenedWriteCase(&doc, landrun)
	runPreopenedExecCase(&doc, landrun)
	for _, kind := range []string{"tcp4", "tcp6", "udp4", "udp6", "unix-path", "unix-abstract"} {
		runNetworkCase(&doc, landrun, kind)
	}
	runInheritedSocketCase(&doc, landrun)

	expectationFailed := applyExpectations(&doc, expects)
	if expectationFailed {
		return doc, 1
	}
	return doc, 0
}

func collectMetadata(landrun string) metadata {
	wd, _ := os.Getwd()
	kernelRelease, releaseErr := readTrimmed("/proc/sys/kernel/osrelease")
	kernelVersion, versionErr := readTrimmed("/proc/version")
	m := metadata{
		PID:              os.Getpid(),
		UID:              os.Getuid(),
		EUID:             os.Geteuid(),
		GoVersion:        runtime.Version(),
		GOOS:             runtime.GOOS,
		GOARCH:           runtime.GOARCH,
		WorkingDirectory: wd,
		KernelRelease:    kernelRelease,
		KernelVersion:    kernelVersion,
		Binaries: map[string]fileIdentity{
			"probe":      identity(probePath),
			"backend":    identity(backendPath),
			"undeclared": identity(otherPath),
		},
		Landrun: identity(landrun),
	}
	if releaseErr != nil {
		m.KernelReleaseError = releaseErr.Error()
	}
	if versionErr != nil {
		m.KernelVersionError = versionErr.Error()
	}
	versionArgv := []string{landrun, "--version"}
	m.LandrunVersion = runProcess(versionArgv, nil, "")
	return m
}

func runIdentityCase(doc *report, landrun string) {
	entry := caseResult{ID: "binary-counted", Description: "Execute the counted probe binary"}
	args := []string{"identify"}
	entry.Control = runObservation("control", landrun, args, nil)
	entry.BestEffort = runObservation("best_effort", landrun, args, nil)
	entry.Strict = runObservation("strict", landrun, args, nil)
	doc.Cases = append(doc.Cases, entry)
}

func runExecCase(doc *report, landrun, id, description, target string, throughFD bool) {
	entry := caseResult{ID: id, Description: description}
	token := newToken()
	var args []string
	var controlFile *os.File
	if throughFD {
		f, err := os.Open(target)
		if err != nil {
			entry.SetupError = "open undeclared executable: " + err.Error()
			doc.Cases = append(doc.Cases, entry)
			return
		}
		controlFile = f
		defer controlFile.Close()
		args = []string{"fd-exec", token}
	} else {
		args = []string{"exec", token, target}
	}
	var files []*os.File
	if controlFile != nil {
		files = []*os.File{controlFile}
	}
	entry.Control = runObservation("control", landrun, args, files)
	entry.BestEffort = runObservation("best_effort", landrun, args, files)
	entry.Strict = runObservation("strict", landrun, args, files)
	doc.Cases = append(doc.Cases, entry)
}

func runSymlinkExecCase(doc *report, landrun, id, description, target string) {
	entry := caseResult{ID: id, Description: description}
	link := filepath.Join(workPath, "link-"+newToken())
	if err := os.Symlink(target, link); err != nil {
		entry.SetupError = "create symlink: " + err.Error()
		doc.Cases = append(doc.Cases, entry)
		return
	}
	args := []string{"exec", id, link}
	entry.Control = runObservation("control", landrun, args, nil)
	entry.BestEffort = runObservation("best_effort", landrun, args, nil)
	entry.Strict = runObservation("strict", landrun, args, nil)
	doc.Cases = append(doc.Cases, entry)
}

func runWriteCase(doc *report, landrun, id, description string, scratch bool) {
	entry := caseResult{ID: id, Description: description}
	observe := func(mode string) *observation {
		token := newToken()
		base := workPath
		if scratch {
			base = scratchPath
		}
		path := filepath.Join(base, "write-"+token)
		if _, err := os.Lstat(path); err == nil {
			return &observation{Mode: mode, SetupError: "unique write target already exists", FilePath: path}
		} else if !errors.Is(err, os.ErrNotExist) {
			return &observation{Mode: mode, SetupError: "inspect write target: " + err.Error(), FilePath: path}
		}
		payload := "cairn-probe-" + token
		r := runObservation(mode, landrun, []string{"write", path, payload}, nil)
		r.FilePath = path
		r.FileCreated, r.FileContent, r.FileContentMatches = inspectFile(path, payload)
		return r
	}
	entry.Control = observe("control")
	entry.BestEffort = observe("best_effort")
	entry.Strict = observe("strict")
	doc.Cases = append(doc.Cases, entry)
}

func runPreopenedWriteCase(doc *report, landrun string) {
	entry := caseResult{ID: "write-preopened-fd", Description: "Write through an inherited preopened outside-scratch file descriptor"}
	observe := func(mode string) *observation {
		token := newToken()
		path := filepath.Join(workPath, "preopened-"+token)
		f, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_RDWR, 0600)
		if err != nil {
			return &observation{Mode: mode, SetupError: "create preopened file: " + err.Error(), FilePath: path}
		}
		defer f.Close()
		payload := "cairn-probe-" + token
		r := runObservation(mode, landrun, []string{"fd-write", payload}, []*os.File{f})
		r.FilePath = path
		r.FileCreated, r.FileContent, r.FileContentMatches = inspectFile(path, payload)
		return r
	}
	entry.Control = observe("control")
	entry.BestEffort = observe("best_effort")
	entry.Strict = observe("strict")
	doc.Cases = append(doc.Cases, entry)
}

func runPreopenedExecCase(doc *report, landrun string) {
	entry := caseResult{ID: "exec-preopened-fd", Description: "Exec an undeclared binary through inherited /proc/self/fd/3"}
	runExecCase(doc, landrun, entry.ID, entry.Description, otherPath, true)
}

func runNetworkCase(doc *report, landrun, kind string) {
	entry := caseResult{ID: "network-" + kind, Description: "Send a fixed payload to a local prestarted listener"}
	observe := func(mode string) *observation {
		token := newToken()
		payload := "cairn-probe-" + token
		control, err := openNetworkControl(kind, token)
		if err != nil {
			return &observation{Mode: mode, SetupError: "start local listener: " + err.Error()}
		}
		defer control.close()
		r := runObservation(mode, landrun, []string{"network", control.kind, control.address, payload}, nil)
		r.ListenerAddress = control.address
		data, readErr := control.read()
		if readErr != nil {
			r.ReceiptError = readErr.Error()
		}
		received := data != nil && len(data) > 0
		exact := string(data) == payload
		r.PayloadReceived = boolPointer(received)
		r.ExactPayloadReceived = boolPointer(exact)
		if received {
			r.ReceivedPayload = string(data)
		}
		return r
	}
	entry.Control = observe("control")
	entry.BestEffort = observe("best_effort")
	entry.Strict = observe("strict")
	doc.Cases = append(doc.Cases, entry)
}

func runInheritedSocketCase(doc *report, landrun string) {
	entry := caseResult{ID: "network-inherited-socket", Description: "Write through an inherited connected TCP4 socket"}
	observe := func(mode string) *observation {
		token := newToken()
		payload := "cairn-probe-" + token
		control, peer, file, err := openConnectedTCP4(token)
		if err != nil {
			if control != nil {
				_ = control.close()
			}
			if peer != nil {
				_ = peer.Close()
			}
			if file != nil {
				_ = file.Close()
			}
			return &observation{Mode: mode, SetupError: "create inherited connected socket: " + err.Error()}
		}
		defer control.close()
		defer peer.Close()
		defer file.Close()
		r := runObservation(mode, landrun, []string{"fd-network", payload}, []*os.File{file})
		r.ListenerAddress = control.address
		_ = peer.SetReadDeadline(time.Now().Add(ioBound))
		data, readErr := io.ReadAll(peer)
		if readErr != nil {
			r.ReceiptError = readErr.Error()
		}
		received := data != nil && len(data) > 0
		r.PayloadReceived = boolPointer(received)
		r.ExactPayloadReceived = boolPointer(string(data) == payload)
		if received {
			r.ReceivedPayload = string(data)
		}
		return r
	}
	entry.Control = observe("control")
	entry.BestEffort = observe("best_effort")
	entry.Strict = observe("strict")
	doc.Cases = append(doc.Cases, entry)
}

func runObservation(mode, landrun string, childArgs []string, extraFiles []*os.File) *observation {
	argv := childArgv(childArgs)
	if mode == "best_effort" || mode == "strict" {
		argv = landrunArgv(mode == "best_effort", landrun, childArgs)
	}
	proc := runProcess(argv, extraFiles, workPath)
	r := &observation{
		Mode:            mode,
		Argv:            proc.Argv,
		PID:             proc.PID,
		ReturnCode:      proc.ReturnCode,
		StartError:      proc.StartError,
		WaitError:       proc.WaitError,
		TimedOut:        proc.TimedOut,
		ElapsedMS:       proc.ElapsedMS,
		Stdout:          proc.Stdout,
		Stderr:          proc.Stderr,
		StdoutTruncated: proc.StdoutTruncated,
		StderrTruncated: proc.StderrTruncated,
	}
	if proc.ChildReport != nil {
		r.ChildReport = proc.ChildReport
		r.ChildStarted = proc.ChildReport.PID > 0
		r.ActionError = proc.ChildReport.ActionError
		succeeded := proc.ChildReport.ActionSucceeded
		if proc.ChildReport.Operation == "identify" && len(childArgs) == 1 && childArgs[0] == "identify" {
			succeeded = true
		} else if proc.ChildReport.Operation == "identify" {
			tag := expectedExecTag(childArgs)
			if tag != "" && proc.ChildReport.ExecTag == tag {
				succeeded = true
			} else {
				succeeded = false
				r.ActionError = fmt.Sprintf("exec identify tag mismatch: got %q, want %q", proc.ChildReport.ExecTag, tag)
				r.ChildParseError = r.ActionError
			}
		}
		r.ActionSucceeded = boolPointer(succeeded)
	} else if strings.TrimSpace(proc.Stdout) != "" {
		r.ChildParseError = "stdout did not contain a child JSON report"
	}
	return r
}

func runProcess(argv []string, extraFiles []*os.File, directory string) processResult {
	ctx, cancel := context.WithTimeout(context.Background(), maxRun)
	defer cancel()
	started := time.Now()
	cmd := exec.CommandContext(ctx, argv[0], argv[1:]...)
	cmd.Env = []string{}
	cmd.Dir = directory
	cmd.ExtraFiles = extraFiles
	cmd.WaitDelay = time.Second
	stdout := &limitedBuffer{limit: 1 << 20}
	stderr := &limitedBuffer{limit: 1 << 20}
	cmd.Stdout = stdout
	cmd.Stderr = stderr
	result := processResult{Argv: append([]string{}, cmd.Args...)}
	if err := cmd.Start(); err != nil {
		result.StartError = err.Error()
		result.ElapsedMS = time.Since(started).Milliseconds()
		result.Stdout = stdout.String()
		result.Stderr = stderr.String()
		result.StdoutTruncated = stdout.truncated
		result.StderrTruncated = stderr.truncated
		return result
	}
	pid := cmd.Process.Pid
	result.PID = &pid
	waitErr := cmd.Wait()
	result.ElapsedMS = time.Since(started).Milliseconds()
	result.Stdout = stdout.String()
	result.Stderr = stderr.String()
	result.StdoutTruncated = stdout.truncated
	result.StderrTruncated = stderr.truncated
	result.TimedOut = errors.Is(ctx.Err(), context.DeadlineExceeded)
	if cmd.ProcessState != nil {
		code := cmd.ProcessState.ExitCode()
		result.ReturnCode = &code
	}
	if waitErr != nil {
		result.WaitError = waitErr.Error()
	}
	trimmed := strings.TrimSpace(result.Stdout)
	if trimmed != "" {
		var child childReport
		if err := json.Unmarshal([]byte(trimmed), &child); err == nil {
			result.ChildReport = &child
		}
	}
	return result
}

func childArgv(args []string) []string {
	argv := []string{probePath, "child"}
	return append(argv, args...)
}

func expectedExecTag(args []string) string {
	if len(args) == 3 && args[0] == "exec" {
		return args[1]
	}
	if len(args) == 2 && args[0] == "fd-exec" {
		return args[1]
	}
	return ""
}

func landrunArgv(bestEffort bool, landrun string, childArgs []string) []string {
	argv := []string{landrun}
	if bestEffort {
		argv = append(argv, "--best-effort")
	}
	argv = append(argv, "--ro", "/", "--rox", probePath+","+backendPath, "--rw", scratchPath, "--", probePath, "child")
	return append(argv, childArgs...)
}

func openNetworkControl(kind, token string) (*networkControl, error) {
	switch kind {
	case "tcp4":
		l, err := net.Listen("tcp4", "127.0.0.1:0")
		if err != nil {
			return nil, err
		}
		listener := l.(*net.TCPListener)
		return &networkControl{kind: "tcp4", address: listener.Addr().String(), close: listener.Close, read: func() ([]byte, error) {
			_ = listener.SetDeadline(time.Now().Add(ioBound))
			conn, err := listener.Accept()
			if err != nil {
				return nil, err
			}
			defer conn.Close()
			_ = conn.SetReadDeadline(time.Now().Add(ioBound))
			return io.ReadAll(conn)
		}}, nil
	case "tcp6":
		l, err := net.Listen("tcp6", "[::1]:0")
		if err != nil {
			return nil, err
		}
		listener := l.(*net.TCPListener)
		return &networkControl{kind: "tcp6", address: listener.Addr().String(), close: listener.Close, read: func() ([]byte, error) {
			_ = listener.SetDeadline(time.Now().Add(ioBound))
			conn, err := listener.Accept()
			if err != nil {
				return nil, err
			}
			defer conn.Close()
			_ = conn.SetReadDeadline(time.Now().Add(ioBound))
			return io.ReadAll(conn)
		}}, nil
	case "udp4":
		p, err := net.ListenPacket("udp4", "127.0.0.1:0")
		if err != nil {
			return nil, err
		}
		return &networkControl{kind: "udp4", address: p.LocalAddr().String(), close: p.Close, read: func() ([]byte, error) {
			_ = p.SetReadDeadline(time.Now().Add(ioBound))
			buf := make([]byte, 4096)
			n, _, err := p.ReadFrom(buf)
			return append([]byte{}, buf[:n]...), err
		}}, nil
	case "udp6":
		p, err := net.ListenPacket("udp6", "[::1]:0")
		if err != nil {
			return nil, err
		}
		return &networkControl{kind: "udp6", address: p.LocalAddr().String(), close: p.Close, read: func() ([]byte, error) {
			_ = p.SetReadDeadline(time.Now().Add(ioBound))
			buf := make([]byte, 4096)
			n, _, err := p.ReadFrom(buf)
			return append([]byte{}, buf[:n]...), err
		}}, nil
	case "unix-path":
		path := filepath.Join(workPath, "unix-"+token+".sock")
		l, err := net.Listen("unix", path)
		if err != nil {
			return nil, err
		}
		listener := l.(*net.UnixListener)
		listener.SetUnlinkOnClose(false)
		return &networkControl{kind: "unix", address: path, close: listener.Close, read: func() ([]byte, error) {
			_ = listener.SetDeadline(time.Now().Add(ioBound))
			conn, err := listener.Accept()
			if err != nil {
				return nil, err
			}
			defer conn.Close()
			_ = conn.SetReadDeadline(time.Now().Add(ioBound))
			return io.ReadAll(conn)
		}}, nil
	case "unix-abstract":
		address := "@cairn-" + token
		l, err := net.Listen("unix", address)
		if err != nil {
			return nil, err
		}
		listener := l.(*net.UnixListener)
		return &networkControl{kind: "unix", address: address, close: listener.Close, read: func() ([]byte, error) {
			_ = listener.SetDeadline(time.Now().Add(ioBound))
			conn, err := listener.Accept()
			if err != nil {
				return nil, err
			}
			defer conn.Close()
			_ = conn.SetReadDeadline(time.Now().Add(ioBound))
			return io.ReadAll(conn)
		}}, nil
	default:
		return nil, fmt.Errorf("unknown network control %q", kind)
	}
}

func openConnectedTCP4(token string) (*networkControl, *net.TCPConn, *os.File, error) {
	l, err := net.ListenTCP("tcp4", &net.TCPAddr{IP: net.IPv4(127, 0, 0, 1)})
	if err != nil {
		return nil, nil, nil, err
	}
	control := &networkControl{kind: "inherited-tcp4", address: l.Addr().String(), close: l.Close}
	clientConn, err := net.DialTimeout("tcp4", l.Addr().String(), ioBound)
	if err != nil {
		return control, nil, nil, err
	}
	client, ok := clientConn.(*net.TCPConn)
	if !ok {
		_ = clientConn.Close()
		return control, nil, nil, errors.New("connected control is not TCP")
	}
	_ = l.SetDeadline(time.Now().Add(ioBound))
	accepted, err := l.AcceptTCP()
	if err != nil {
		_ = client.Close()
		return control, nil, nil, err
	}
	file, err := client.File()
	if err != nil {
		_ = client.Close()
		_ = accepted.Close()
		return control, nil, nil, err
	}
	_ = client.Close()
	return control, accepted, file, nil
}

func inspectFile(path, expected string) (*bool, string, *bool) {
	_, err := os.Lstat(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return boolPointer(false), "", boolPointer(false)
		}
		return nil, "", nil
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return boolPointer(true), "", nil
	}
	content := string(data)
	return boolPointer(true), content, boolPointer(content == expected)
}

func applyExpectations(doc *report, expressions []string) bool {
	failed := false
	for _, expression := range expressions {
		parsed, parseErr := parseExpectation(expression)
		if parseErr != nil {
			doc.Expectations = append(doc.Expectations, expectationResult{Expression: expression, Passed: false})
			failed = true
			continue
		}
		actual := findExpectationValue(doc.Cases, parsed.caseID, parsed.run, parsed.field)
		passed := actual != nil && *actual == parsed.expected
		doc.Expectations = append(doc.Expectations, expectationResult{Expression: expression, Expected: parsed.expected, Actual: actual, Passed: passed})
		if !passed {
			failed = true
		}
	}
	return failed
}

type parsedExpectation struct {
	caseID   string
	run      string
	field    string
	expected bool
}

func parseExpectation(value string) (parsedExpectation, error) {
	parts := strings.SplitN(value, "=", 2)
	if len(parts) != 2 {
		return parsedExpectation{}, errors.New("expectation requires CASE:RUN:FIELD=BOOL")
	}
	left := strings.Split(parts[0], ":")
	if len(left) != 3 || left[0] == "" {
		return parsedExpectation{}, errors.New("expectation requires CASE:RUN:FIELD=BOOL")
	}
	if left[1] != "control" && left[1] != "best_effort" && left[1] != "strict" {
		return parsedExpectation{}, errors.New("expectation run must be control, best_effort, or strict")
	}
	if left[2] != "child_started" && left[2] != "action_succeeded" && left[2] != "payload_received" && left[2] != "exact_payload_received" && left[2] != "file_created" && left[2] != "file_content_matches" {
		return parsedExpectation{}, errors.New("unsupported expectation field")
	}
	expected, err := parseBool(parts[1])
	if err != nil {
		return parsedExpectation{}, errors.New("expectation value must be true or false")
	}
	return parsedExpectation{caseID: left[0], run: left[1], field: left[2], expected: expected}, nil
}

func findExpectationValue(cases []caseResult, caseID, run, field string) *bool {
	for _, c := range cases {
		if c.ID != caseID {
			continue
		}
		var r *observation
		switch run {
		case "control":
			r = c.Control
		case "best_effort":
			r = c.BestEffort
		case "strict":
			r = c.Strict
		}
		if r == nil {
			return nil
		}
		switch field {
		case "child_started":
			return boolPointer(r.ChildStarted)
		case "action_succeeded":
			return r.ActionSucceeded
		case "payload_received":
			return r.PayloadReceived
		case "exact_payload_received":
			return r.ExactPayloadReceived
		case "file_created":
			return r.FileCreated
		case "file_content_matches":
			return r.FileContentMatches
		}
	}
	return nil
}

func identity(path string) fileIdentity {
	result := fileIdentity{Path: path}
	f, err := os.Open(path)
	if err != nil {
		result.Error = err.Error()
		return result
	}
	defer f.Close()
	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		result.Error = err.Error()
		return result
	}
	result.SHA256 = hex.EncodeToString(h.Sum(nil))
	return result
}

func executablePath() string {
	path, err := os.Executable()
	if err != nil {
		return ""
	}
	return path
}

func readTrimmed(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(data)), nil
}

func newToken() string {
	data := make([]byte, 12)
	_, _ = rand.Read(data)
	return hex.EncodeToString(data)
}

func parseBool(value string) (bool, error) {
	switch value {
	case "true":
		return true, nil
	case "false":
		return false, nil
	default:
		return false, errors.New("not a boolean")
	}
}

func boolPointer(value bool) *bool {
	return &value
}

func errorString(err error) string {
	if err == nil {
		return ""
	}
	return err.Error()
}

func writeJSON(value any) {
	_ = json.NewEncoder(os.Stdout).Encode(value)
}
