#include <dlfcn.h>
#include <stddef.h>
#include <stdio.h>

// Handle to the real OpenCL library
static void* ocl_handle = NULL;

static void init_ocl() {
    if (!ocl_handle) {
        ocl_handle = dlopen("libOpenCL.so", RTLD_NOW | RTLD_LOCAL);
        if (!ocl_handle) ocl_handle = dlopen("/vendor/lib64/libOpenCL.so", RTLD_NOW | RTLD_LOCAL);
        if (!ocl_handle) ocl_handle = dlopen("/system/vendor/lib64/libOpenCL.so", RTLD_NOW | RTLD_LOCAL);
        if (!ocl_handle) ocl_handle = dlopen("/system/lib64/libOpenCL.so", RTLD_NOW | RTLD_LOCAL);
    }
}

// Helper to resolve symbols
static void* get_sym(const char* name) {
    if (!ocl_handle) init_ocl();
    if (ocl_handle) return dlsym(ocl_handle, name);
    return NULL;
}

// OpenCL API Stubs
// For basic GGML init, we need these to at least not crash, and ideally proxy to real functions.

int clGetPlatformIDs(unsigned int num_entries, void *platforms, unsigned int *num_platforms) {
    int (*real_clGetPlatformIDs)(unsigned int, void*, unsigned int*) = get_sym("clGetPlatformIDs");
    if (real_clGetPlatformIDs) return real_clGetPlatformIDs(num_entries, platforms, num_platforms);
    if (num_platforms) *num_platforms = 0;
    return -1001; // CL_PLATFORM_NOT_FOUND_KHR
}

int clGetDeviceIDs(void *platform, unsigned long device_type, unsigned int num_entries, void *devices, unsigned int *num_devices) {
    int (*real_clGetDeviceIDs)(void*, unsigned long, unsigned int, void*, unsigned int*) = get_sym("clGetDeviceIDs");
    if (real_clGetDeviceIDs) return real_clGetDeviceIDs(platform, device_type, num_entries, devices, num_devices);
    if (num_devices) *num_devices = 0;
    return -1; // CL_DEVICE_NOT_FOUND
}

void clBuildProgram() { void* f = get_sym("clBuildProgram"); if(f) ((void(*)())f)(); }
void clCreateBuffer() { void* f = get_sym("clCreateBuffer"); if(f) ((void(*)())f)(); }
void clCreateCommandQueue() { void* f = get_sym("clCreateCommandQueue"); if(f) ((void(*)())f)(); }
void clCreateContext() { void* f = get_sym("clCreateContext"); if(f) ((void(*)())f)(); }
void clCreateImage() { void* f = get_sym("clCreateImage"); if(f) ((void(*)())f)(); }
void clCreateKernel() { void* f = get_sym("clCreateKernel"); if(f) ((void(*)())f)(); }
void clCreateProgramWithSource() { void* f = get_sym("clCreateProgramWithSource"); if(f) ((void(*)())f)(); }
void clCreateSubBuffer() { void* f = get_sym("clCreateSubBuffer"); if(f) ((void(*)())f)(); }
void clEnqueueBarrierWithWaitList() { void* f = get_sym("clEnqueueBarrierWithWaitList"); if(f) ((void(*)())f)(); }
void clEnqueueCopyBuffer() { void* f = get_sym("clEnqueueCopyBuffer"); if(f) ((void(*)())f)(); }
void clEnqueueFillBuffer() { void* f = get_sym("clEnqueueFillBuffer"); if(f) ((void(*)())f)(); }
void clEnqueueMarkerWithWaitList() { void* f = get_sym("clEnqueueMarkerWithWaitList"); if(f) ((void(*)())f)(); }
void clEnqueueNDRangeKernel() { void* f = get_sym("clEnqueueNDRangeKernel"); if(f) ((void(*)())f)(); }
void clEnqueueReadBuffer() { void* f = get_sym("clEnqueueReadBuffer"); if(f) ((void(*)())f)(); }
void clEnqueueWriteBuffer() { void* f = get_sym("clEnqueueWriteBuffer"); if(f) ((void(*)())f)(); }
void clFinish() { void* f = get_sym("clFinish"); if(f) ((void(*)())f)(); }
void clFlush() { void* f = get_sym("clFlush"); if(f) ((void(*)())f)(); }
void clGetDeviceInfo() { void* f = get_sym("clGetDeviceInfo"); if(f) ((void(*)())f)(); }
void clGetEventProfilingInfo() { void* f = get_sym("clGetEventProfilingInfo"); if(f) ((void(*)())f)(); }
void clGetKernelInfo() { void* f = get_sym("clGetKernelInfo"); if(f) ((void(*)())f)(); }
void clGetKernelSubGroupInfo() { void* f = get_sym("clGetKernelSubGroupInfo"); if(f) ((void(*)())f)(); }
void clGetKernelWorkGroupInfo() { void* f = get_sym("clGetKernelWorkGroupInfo"); if(f) ((void(*)())f)(); }
void clGetPlatformInfo() { void* f = get_sym("clGetPlatformInfo"); if(f) ((void(*)())f)(); }
void clGetProgramBuildInfo() { void* f = get_sym("clGetProgramBuildInfo"); if(f) ((void(*)())f)(); }
void clReleaseCommandQueue() { void* f = get_sym("clReleaseCommandQueue"); if(f) ((void(*)())f)(); }
void clReleaseContext() { void* f = get_sym("clReleaseContext"); if(f) ((void(*)())f)(); }
void clReleaseEvent() { void* f = get_sym("clReleaseEvent"); if(f) ((void(*)())f)(); }
void clReleaseKernel() { void* f = get_sym("clReleaseKernel"); if(f) ((void(*)())f)(); }
void clReleaseMemObject() { void* f = get_sym("clReleaseMemObject"); if(f) ((void(*)())f)(); }
void clReleaseProgram() { void* f = get_sym("clReleaseProgram"); if(f) ((void(*)())f)(); }
void clSetKernelArg() { void* f = get_sym("clSetKernelArg"); if(f) ((void(*)())f)(); }
void clWaitForEvents() { void* f = get_sym("clWaitForEvents"); if(f) ((void(*)())f)(); }
void clGetExtensionFunctionAddressForPlatform() { void* f = get_sym("clGetExtensionFunctionAddressForPlatform"); if(f) ((void(*)())f)(); }
void clSetUserEventStatus() { void* f = get_sym("clSetUserEventStatus"); if(f) ((void(*)())f)(); }
void clReleaseDevice() { void* f = get_sym("clReleaseDevice"); if(f) ((void(*)())f)(); }
void clRetainEvent() { void* f = get_sym("clRetainEvent"); if(f) ((void(*)())f)(); }
void clGetEventInfo() { void* f = get_sym("clGetEventInfo"); if(f) ((void(*)())f)(); }
void clCreateUserEvent() { void* f = get_sym("clCreateUserEvent"); if(f) ((void(*)())f)(); }
